import yaml


def yaml_enum(cls):
    yaml_tag = f"!{cls.__name__}"

    def enum_representer(dumper, data):
        return dumper.represent_scalar(yaml_tag, data.name)

    def enum_constructor(loader, node):
        value = loader.construct_scalar(node)
        return cls[value]

    yaml.add_multi_representer(cls, enum_representer)
    yaml.add_constructor(yaml_tag, enum_constructor)

    return cls
