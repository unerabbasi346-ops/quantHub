# Governing specification: Doc 03 — Technology Stack §Quantitative Libraries
#   (XGBoost, PyTorch, scikit-learn already listed there).
# Layer: Domain-adjacent ML models — Doc 04 §Repository Structure src-layout.
# Per Doc 00 §14.11
#
# RELOCATED (Task 0/2 audit): originally a floating backend/ml/ml_engine.py
# outside the src/ layout Doc 04 mandates for this repo, and outside any
# installed package (`[tool.setuptools.packages.find] where = ["src"]`
# never discovered it) — `import ml_engine` was unreachable from the running
# application. Moved to src/quant_hub/ml/ so model_factory.py and the /api/ml
# router can actually import it. Class bodies are UNCHANGED except the
# LSTMPredictor fix noted on that class (nn.Module inheritance + the
# train()/eval() method-name collision with its own abstract train()).
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional
import joblib
import os

# ML Imports
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, mean_squared_error
from hmmlearn.hmm import GaussianHMM

# PyTorch for Deep Learning
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# ==========================================
# 1. CORE ABSTRACT BASE CLASS
# ==========================================
class BaseQuantModel(ABC):
    """
    Abstract base class for all quantitative ML models.
    Ensures every model has a consistent API for the dashboard to interact with.
    """
    def __init__(self, model_name: str, params: Dict[str, Any]):
        self.model_name = model_name
        self.params = params
        self.model = None
        self.scaler = StandardScaler() # Crucial for neural nets and distance-based models
        self.is_trained = False

    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series, X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None):
        """Trains the model on feature matrix X and target y."""
        pass

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generates predictions. Returns probabilities for classifiers, values for regressors."""
        pass

    @abstractmethod
    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
        """Returns a dictionary of relevant metrics (e.g., accuracy, RMSE, precision)."""
        pass

    def save_model(self, filepath: str):
        """Saves the trained model and scaler to disk."""
        if not self.is_trained:
            raise ValueError("Model is not trained yet.")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({'model': self.model, 'scaler': self.scaler}, filepath)

    def load_model(self, filepath: str):
        """Loads a trained model and scaler from disk."""
        data = joblib.load(filepath)
        self.model = data['model']
        self.scaler = data['scaler']
        self.is_trained = True


# ==========================================
# 2. TREE-BASED MODEL: META-LABELER
# ==========================================
class XGBoostMetaLabeler(BaseQuantModel):
    """
    Uses XGBoost to predict the probability that an existing strategy's signal 
    will be profitable. (Marcos Lopez de Prado methodology).
    Target y should be 1 (profitable trade) or 0 (unprofitable trade).
    """
    def __init__(self, params: Dict[str, Any] = None):
        default_params = {'max_depth': 5, 'learning_rate': 0.05, 'n_estimators': 200, 'eval_metric': 'logloss'}
        if params:
            default_params.update(params)
        super().__init__("XGBoost_MetaLabeler", default_params)

    def train(self, X: pd.DataFrame, y: pd.Series, X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None):
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        eval_set = [(X_scaled, y)]
        if X_val is not None and y_val is not None:
            X_val_scaled = self.scaler.transform(X_val)
            eval_set.append((X_val_scaled, y_val))

        self.model = xgb.XGBClassifier(**self.params)
        self.model.fit(X_scaled, y, eval_set=eval_set, verbose=False)
        self.is_trained = True

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            raise ValueError("Model not trained.")
        X_scaled = self.scaler.transform(X)
        # Return probability of class 1 (probability of success)
        return self.model.predict_proba(X_scaled)[:, 1]

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
        X_scaled = self.scaler.transform(X_test)
        y_pred_proba = self.model.predict_proba(X_scaled)[:, 1]
        y_pred_class = (y_pred_proba > 0.5).astype(int)
        
        # Feature importance is crucial for UI dashboards
        feature_importance = dict(zip(X_test.columns, self.model.feature_importances_))
        
        return {
            "accuracy": accuracy_score(y_test, y_pred_class),
            "precision": precision_score(y_test, y_pred_class, zero_division=0),
            "recall": recall_score(y_test, y_pred_class, zero_division=0),
            "feature_importance": feature_importance
        }


# ==========================================
# 3. DEEP LEARNING: LSTM TIME-SERIES PREDICTOR
# ==========================================
class LSTMSequenceDataset(torch.utils.data.Dataset):
    """Helper class to format time-series data into sequences for LSTM."""
    def __init__(self, X: np.ndarray, y: np.ndarray, seq_length: int):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32)
        self.seq_length = seq_length

    def __len__(self):
        return len(self.X) - self.seq_length

    def __getitem__(self, idx):
        return self.X[idx:idx+self.seq_length], self.y[idx+self.seq_length]

class LSTMPredictor(BaseQuantModel, nn.Module):
    """
    PyTorch LSTM for predicting future returns or prices.

    BUG FIX (Task 0 audit, flagged): this class previously extended only
    BaseQuantModel (a plain ABC), never nn.Module, while its train()/predict()
    bodies called self.parameters() and self.train()/self.eval() as if it
    were one — self.parameters() doesn't exist without the nn.Module base,
    and self.train()/self.eval() collided with THIS class's own train()
    override (a method-name clash with PyTorch's mode-toggle), causing
    self.train() to recurse into itself with the wrong argument count. Fixed
    by (1) actually inheriting nn.Module and explicitly calling both parent
    __init__s (BaseQuantModel's doesn't chain via super(), so nn.Module's
    never ran), and (2) calling nn.Module.train(self, ...) directly instead
    of self.train()/self.eval(), bypassing the name collision.
    """
    def __init__(self, params: Dict[str, Any] = None):
        default_params = {
            'input_dim': 10,
            'hidden_dim': 64,
            'num_layers': 2,
            'output_dim': 1,
            'epochs': 50,
            'batch_size': 32,
            'learning_rate': 0.001,
            'seq_length': 14 # Lookback window
        }
        if params:
            default_params.update(params)
        # nn.Module.__init__ MUST run before any submodule (nn.LSTM/nn.Linear)
        # is assigned as an attribute below — it sets up the internal
        # _modules/_parameters registries nn.Module.__setattr__ relies on.
        nn.Module.__init__(self)
        BaseQuantModel.__init__(self, "LSTM_Predictor", default_params)

        # Define network architecture
        self.seq_length = self.params['seq_length']
        self.lstm = nn.LSTM(
            input_size=self.params['input_dim'],
            hidden_size=self.params['hidden_dim'],
            num_layers=self.params['num_layers'],
            batch_first=True
        )
        self.linear = nn.Linear(self.params['hidden_dim'], self.params['output_dim'])

    def train(self, X: pd.DataFrame, y: pd.Series, X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None):
        X_scaled = self.scaler.fit_transform(X)
        y_arr = y.values.reshape(-1, 1)

        dataset = LSTMSequenceDataset(X_scaled, y_arr, self.seq_length)
        dataloader = DataLoader(dataset, batch_size=self.params['batch_size'], shuffle=False)

        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.parameters(), lr=self.params['learning_rate'])

        nn.Module.train(self, True)  # PyTorch train mode (not self.train() — name collision)
        for epoch in range(self.params['epochs']):
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                outputs, _ = self.lstm(batch_X)
                outputs = self.linear(outputs[:, -1, :]) # Take last time step
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()

        self.is_trained = True

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            raise ValueError("Model not trained.")
        nn.Module.train(self, False)  # PyTorch eval mode (not self.eval() — same collision risk)
        X_scaled = self.scaler.transform(X)
        X_tensor = torch.tensor(X_scaled, dtype=torch.float32).unsqueeze(0) # Add batch dim

        with torch.no_grad():
            outputs, _ = self.lstm(X_tensor)
            preds = self.linear(outputs[:, -1, :])
        return preds.numpy().flatten()

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> Dict[str, float]:
        preds = self.predict(X_test)
        # Align y_test with predictions (dropping initial sequence length)
        y_true = y_test.values[self.seq_length:].flatten()
        preds = preds[:len(y_true)] # Ensure alignment

        # Calculate Directional Accuracy (Did we guess up/down correctly?)
        actual_direction = np.sign(np.diff(y_true))
        pred_direction = np.sign(np.diff(preds))
        dir_accuracy = np.mean(actual_direction == pred_direction)

        return {
            "rmse": np.sqrt(mean_squared_error(y_true, preds)),
            "directional_accuracy": dir_accuracy
        }

    def save_model(self, filepath: str):
        # Override: BaseQuantModel.save_model dumps self.model, which
        # LSTMPredictor never sets (its real state lives in the nn.Module's
        # own lstm/linear submodules) — persist the actual state_dict instead.
        if not self.is_trained:
            raise ValueError("Model is not trained yet.")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({'state_dict': self.state_dict(), 'scaler': self.scaler, 'params': self.params}, filepath)

    def load_model(self, filepath: str):
        data = joblib.load(filepath)
        self.load_state_dict(data['state_dict'])
        self.scaler = data['scaler']
        self.is_trained = True

# ==========================================
# 4. UNSUPERVISED LEARNING: REGIME DETECTION
# ==========================================
class HMMRegimeDetector(BaseQuantModel):
    """
    Hidden Markov Model to detect market regimes (e.g., Bull, Bear, Choppy).
    Inputs typically: Returns, Volatility.
    """
    def __init__(self, params: Dict[str, Any] = None):
        default_params = {'n_components': 3, 'covariance_type': "full", 'n_iter': 100}
        if params:
            default_params.update(params)
        super().__init__("HMM_RegimeDetector", default_params)
        self.model = GaussianHMM(**self.params)

    def train(self, X: pd.DataFrame, y: pd.Series = None, X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None):
        # HMM is unsupervised, so y is ignored.
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled)
        self.is_trained = True
        
        # Map states to regimes based on mean returns (heuristic)
        # This allows the UI to color-code regimes meaningfully
        regime_means = []
        for i in range(self.params['n_components']):
            state_data = X_scaled[self.model.predict(X_scaled) == i]
            if len(state_data) > 0:
                regime_means.append(np.mean(state_data[:, 0])) # Assuming column 0 is returns
            else:
                regime_means.append(0)
                
        # Sort states: lowest mean = Bear, highest mean = Bull
        self.regime_mapping = {i: regime for i, regime in enumerate(np.argsort(np.argsort(regime_means)))}

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            raise ValueError("Model not trained.")
        X_scaled = self.scaler.transform(X)
        raw_states = self.model.predict(X_scaled)
        # Return mapped regimes (e.g., 0 = Bear, 1 = Sideways, 2 = Bull)
        return np.array([self.regime_mapping[s] for s in raw_states])

    def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series = None) -> Dict[str, float]:
        # For unsupervised models, traditional metrics don't apply.
        # We return the mean duration of each regime, which is useful for strategy design.
        regimes = self.predict(X_test)
        durations = {i: [] for i in range(self.params['n_components'])}
        current_regime = regimes[0]
        count = 1
        
        for r in regimes[1:]:
            if r == current_regime:
                count += 1
            else:
                durations[current_regime].append(count)
                current_regime = r
                count = 1
        durations[current_regime].append(count)
        
        avg_durations = {f"regime_{k}_avg_duration": np.mean(v) if v else 0 for k, v in durations.items()}
        return avg_durations

    def save_model(self, filepath: str):
        # Override because hmmlearn handles persistence differently sometimes
        if not self.is_trained:
            raise ValueError("Model is not trained yet.")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({'model': self.model, 'scaler': self.scaler, 'regime_mapping': self.regime_mapping}, filepath)

    def load_model(self, filepath: str):
        data = joblib.load(filepath)
        self.model = data['model']
        self.scaler = data['scaler']
        self.regime_mapping = data['regime_mapping']
        self.is_trained = True