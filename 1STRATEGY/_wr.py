import sys, os  
sys.stdout.reconfigure(encoding='utf-8')  
target = r'..\backend\src\quant_hub\application\strategy_engine\reference_strategies\funding_rate_basis.py'  
os.makedirs(os.path.dirname(target), exist_ok=True) 
