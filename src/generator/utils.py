import yaml

def load_config(path: str):
    if not path:
        return ValueError("Config path can not be empty ! ")
    with open(path, 'r', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)
    return cfg

