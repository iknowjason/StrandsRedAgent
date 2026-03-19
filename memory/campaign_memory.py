campaign_memory = {
    "target": None,
    "osint": {},
    "social_engineering": {},
}


def initialize(target):
    campaign_memory["target"] = target


def update(section, key, value):
    if section not in campaign_memory:
        campaign_memory[section] = {}
    campaign_memory[section][key] = value


def get(section):
    return campaign_memory.get(section, {})


def get_all():
    return campaign_memory
