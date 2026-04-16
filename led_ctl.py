import importlib.util

file_path = "/home/pi/sensestorm3-rcu/src/rcu.py"
module_name = "my_module"

spec = importlib.util.spec_from_file_location(module_name, file_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
led_func = getattr(module, "set_color_light")


def led_on():
    led_func(1,7)

def led_off():
    led_func(1,0)

led_off()
