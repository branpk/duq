from dataclasses import dataclass
import inspect
from inspect import Parameter
from types import UnionType
import typing
from typing import Any, Callable

from duq._syntax import Expr, LiteralExpr, OpExpr


class DuqTypeError(Exception):
    pass


def type_check_value(value: Any, annotation: Any) -> None:
    if annotation is Any:
        pass
    elif annotation is Expr:
        if type(value) not in [LiteralExpr, OpExpr]:
            raise DuqTypeError(
                f"expected expression, found type `{type(value).__name__}`"
            )
    elif annotation in [int, float, str, bool]:
        if type(value) is not annotation:
            raise DuqTypeError(
                f"expected type `{annotation.__name__}`, found type `{type(value).__name__}`"
            )
    elif typing.get_origin(annotation) == list:
        element_type = typing.get_args(annotation)[0]
        if type(value) is not list:
            raise DuqTypeError(
                f"expected type `{annotation.__name__}`, found type `{type(value).__name__}`"
            )
        for element in value:
            type_check_value(element, element_type)
    elif type(annotation) is UnionType:
        for type_opt in typing.get_args(annotation):
            try:
                type_check_value(value, type_opt)
                break
            except DuqTypeError:
                pass
        else:
            raise DuqTypeError(
                f"expected type `{annotation}`, found type `{type(value).__name__}`"
            )
    elif annotation is inspect._empty:
        raise Exception(f"missing type annotation")
    else:
        raise Exception(f"unimplemented type annotation: `{annotation}`")


@dataclass
class OpSignature:
    name_parts: list[str]
    input_param: Parameter | None
    is_macro: bool
    req_arg_params: list[Parameter]
    opt_arg_params: list[Parameter]
    var_args_param: Parameter | None

    @staticmethod
    def of(name: str, op_func: Callable) -> "OpSignature":
        name_parts = name.split(".")
        if len(name_parts) != 3:
            raise Exception(
                f"`{name}`: op name must have form `<package>.<namespace>.<op>`"
            )

        signature = inspect.signature(op_func)

        input_param: Parameter | None = None
        req_arg_params: list[Parameter] = []
        opt_arg_params: list[Parameter] = []
        var_args_param: Parameter | None = None

        for i, param in enumerate(signature.parameters.values()):
            if param.name == "input":
                if i != 0:
                    raise Exception(f"`{name}`: `input` must be the first parameter")
                if param.kind != Parameter.POSITIONAL_OR_KEYWORD:
                    raise Exception(f"`{name}`: invalid input parameter: `{param}`")
                input_param = param
            elif param.kind == Parameter.POSITIONAL_OR_KEYWORD:
                if param.default is inspect._empty:
                    req_arg_params.append(param)
                else:
                    opt_arg_params.append(param)
            elif param.kind == Parameter.VAR_POSITIONAL:
                var_args_param = param
            else:
                raise Exception(f"`{name}`: invalid op parameter: {param}")

        all_arg_params = (
            req_arg_params
            + opt_arg_params
            + ([] if var_args_param is None else [var_args_param])
        )
        any_expr_args = False
        all_expr_args = True
        for param in all_arg_params:
            is_expr_arg = param.annotation is Expr
            any_expr_args |= is_expr_arg
            all_expr_args &= is_expr_arg
        is_macro = any_expr_args
        if is_macro and not all_expr_args:
            raise Exception(f"`{name}`: mix of Expr and concrete op parameters")

        return OpSignature(
            name_parts=name_parts,
            input_param=input_param,
            is_macro=is_macro,
            req_arg_params=req_arg_params,
            opt_arg_params=opt_arg_params,
            var_args_param=var_args_param,
        )

    def type_check_inputs(self, input: Any, args: tuple[Any, ...]) -> None:
        if self.input_param:
            type_check_value(input, self.input_param.annotation)

        req_params = self.req_arg_params
        opt_params = self.opt_arg_params
        var_param = self.var_args_param

        n_args_text = lambda n: f"{n} argument" if n == 1 else f"{n} arguments"

        if len(opt_params) == 0 and var_param is None and len(args) != len(req_params):
            raise DuqTypeError(
                f"expected {n_args_text(len(req_params))}, {len(args)} given"
            )
        elif len(args) < len(req_params):
            raise DuqTypeError(
                f"expected at least {n_args_text(len(req_params))}, {len(args)} given"
            )
        elif var_param is None and len(args) > len(req_params) + len(opt_params):
            raise DuqTypeError(
                f"expected at most {n_args_text(len(req_params) + len(opt_params))}, {len(args)} given"
            )

        for param, arg in zip(req_params, args):
            type_check_value(arg, param.annotation)
        for param, arg in zip(opt_params, args[len(req_params) :]):
            type_check_value(arg, param.annotation)
        for arg in args[len(req_params) + len(opt_params) :]:
            assert var_param is not None
            type_check_value(arg, var_param.annotation)

    def get_call_args(self, input: Any, args: tuple[Any, ...]) -> list[Any]:
        call_args = []
        if self.input_param:
            call_args.append(input)
        call_args += args
        return call_args
