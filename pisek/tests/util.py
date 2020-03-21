from ..task_config import TaskConfig
from .kasiopea_test_suite import kasiopea_test_suite
from .cms_test_suite import cms_test_suite

def get_test_suite(dir, **kwargs):
    config = TaskConfig(dir)

    suites_dict = {
        "kasiopea": kasiopea_test_suite,
        "cms": cms_test_suite,
    }

    try:
        suite = suites_dict[config.contest_type](dir, **kwargs)
    except KeyError:
        raise KeyError(
            f"Neznámý typ soutěže '{config.contest_type}'. "
            f"Znám typy {list(suites_dict)}",
        )

    return suite
