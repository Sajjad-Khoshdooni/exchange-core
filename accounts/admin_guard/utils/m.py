from .bool_node import BoolNode


class Superuser(BoolNode):
    def leaf_evaluator(self, request, admin, model, condition):
        return request.user.is_superuser


class HasPerm(BoolNode):
    def leaf_evaluator(self, request, admin, model, condition):
        return request.user.has_perm(condition)


class M(BoolNode):
    superuser = Superuser()
    has_perm = HasPerm

    def leaf_evaluator(self, request, admin, model, condition):
        if isinstance(condition, str):

            if hasattr(admin, condition):
                admin_func = getattr(admin, condition, None)
                return admin_func(model)

            elif hasattr(model, condition):
                return getattr(model, condition)

            else:
                raise Exception('condition not found')

        elif callable(condition):
            return condition(admin, model)

        else:
            return bool(condition)
