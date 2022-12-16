def mark_on_exit(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        finally:
            s = args[0]
            s.connected = False
            s.active_tunnel = None
            s.response = None

    return wrapper


def resolve_context(func):
    def wrapper(*args, **kwargs):
        if len(args) == 1 or (len(args) > 2 and args[1] is None):
            from abst.bastion_support.oci_bastion import Bastion
            conf = Bastion.load_config()
            func(args[0], conf["used_context"], **kwargs)
        else:
            return func(*args)

    return wrapper


def load_stack_decorator(func):
    def wrapper(*args, **kwargs):
        args[0].load_stack()
        return func(*args, **kwargs)

    return wrapper
