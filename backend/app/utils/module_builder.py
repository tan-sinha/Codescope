from app.data.module import ModuleInfo


def build_module(
    file_path,
    functions,
    classes,
    imports,
):
    module = ModuleInfo(
        path=file_path
    )

    module.functions = [
        fn.name
        for fn in functions
    ]

    module.classes = [
        cls.name
        for cls in classes
    ]

    module.imports = [
        imp.module
        for imp in imports
    ]

    return module