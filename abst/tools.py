from abst.config import default_creds_path, default_contexts_location


def get_context_path(context_name):
    if context_name is None:
        return default_creds_path
    else:
        return default_contexts_location / (context_name + ".json")
