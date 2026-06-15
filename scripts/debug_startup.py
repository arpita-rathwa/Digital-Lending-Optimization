"""Debug API startup."""
import os
print("CWD:", os.getcwd())
print("DB exists:", os.path.exists("digital_lending.db"))
print("Model exists:", os.path.exists("models/xgb_default.pkl"))

from lendiql.models import init_on_startup, get_startup_error, _models
init_on_startup()
err = get_startup_error()
print("Startup error:", err)
print("Models loaded:", list(_models.keys()))
