import json
import ac

class ConfigurationUtility:
  def __init__(self, config_file_name):
    self.config_file_name = config_file_name
    self.config = {}
    try:
      with open(config_file_name) as file:
        self.config = json.load(file)
    except FileNotFoundError:
      ac.log("File not found!")
    except json.JSONDecodeError:
      ac.log("Failed to parse JSON")
  
  def get_or_default(self, key, default):
    if self.config and self.config[key]:
      return self.config[key]
    else: 
      return default
  
  def set_value(self, key, value):
    self.config[key] = value
  
  def save_config(self):
    with open(self.config_file_name, "w") as output_file:
      json.dump(self.config, output_file)
