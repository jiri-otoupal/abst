class BastionScheduler:
    __stack = []

    @classmethod
    def add_bastion(cls, single):
        pass

    @classmethod
    def kill_all(cls, a=None, b=None, c=None):
        for bastion in cls.__stack:
            bastion.kill()

    @classmethod
    def get_bastions(cls) -> tuple:
        return tuple(cls.__stack)
