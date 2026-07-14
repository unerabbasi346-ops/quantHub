# Hermes — read-only system-observability layer.
#
# ARCHITECTURAL BOUNDARY (hard constraint, verified by
# tests/unit/hermes/test_import_boundary.py): nothing under this package may
# import quant_hub.domain.strategy_engine, quant_hub.domain.portfolio,
# quant_hub.domain.execution, quant_hub.domain.risk, or their
# application/persistence-repository counterparts. Hermes coordinates and
# monitors ONLY — it reports on the financial pipeline from the outside,
# via direct read-only SQL against the tables those layers own, never by
# calling into their domain/application code. No signal generation, no
# order execution, no risk evaluation, no portfolio math lives here.
