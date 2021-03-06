# Copyright: 2010-2011 Brian Harring <ferringb@gmail.com>
# License: GPL2/BSD 3 clause

from snakeoil.test import mixins


class ExportedModules(mixins.PythonNamespaceWalker):

    target_namespace = 'snakeoil'

    def test__all__accuracy(self):
        failures = []
        for module in self.walk_namespace(self.target_namespace):
            for target in getattr(module, '__all__', ()):
                if not hasattr(module, target):
                    failures.append((module, target))
        assert not failures, "nonexistent __all__ targets spotted: %s" % (failures,)
