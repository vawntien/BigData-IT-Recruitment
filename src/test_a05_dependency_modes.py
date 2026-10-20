import unittest
from a05_spark import prepare_dependencies


class DependencyModeTests(unittest.TestCase):
    def test_shared_environment_refuses_remote_master(self):
        class Context:
            master='spark://cluster:7077'
        with self.assertRaisesRegex(ValueError,'single-host'):
            prepare_dependencies(Context(),'shared_local_pythonpath')

    def test_unknown_mode_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'Unknown'):
            prepare_dependencies(object(),'auto_skip')

    def test_standard_distribution_includes_adapter_module(self):
        class Context:
            paths=[]
            def addPyFile(self,path):self.paths.append(path)
        sc=Context();prepare_dependencies(sc,'add_pyfile')
        self.assertEqual(len(sc.paths),4)
        self.assertTrue(any(p.endswith('a05_spark.py') for p in sc.paths))
