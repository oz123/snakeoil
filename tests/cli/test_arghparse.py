# Copyright: 2015 Tim Harder <radhermit@gmail.com>
# License: GPL2/BSD 3 clause

import argparse
from functools import partial
from importlib import reload
import os
import tempfile
from unittest import TestCase, mock

from snakeoil.cli import arghparse
from snakeoil.test import argparse_helpers


class TestArgparseDocs(TestCase):

    def test_add_argument_docs(self):
        # force using an unpatched version of argparse
        reload(argparse)

        parser = argparse.ArgumentParser()
        parser.add_argument('--foo', action='store_true')

        # vanilla argparse doesn't support docs kwargs
        with self.assertRaises(TypeError):
            parser.add_argument(
                '-b', '--blah', action='store_true', docs='Blah blah blah')
        with self.assertRaises(TypeError):
            parser.add_argument_group('fa', description='fa la la', docs='fa la la la')
        with self.assertRaises(TypeError):
            parser.add_mutually_exclusive_group('fee', description='fi', docs='fo fum')

        # forcibly monkey-patch argparse to allow docs kwargs
        reload(arghparse)

        default = 'baz baz'
        docs = 'blah blah'
        for enable_docs, expected_txt in ((False, default), (True, docs)):
            arghparse._generate_docs = enable_docs
            parser = argparse.ArgumentParser()
            subparsers = parser.add_subparsers(description=default, docs=docs)
            subparser = subparsers.add_parser('foo', description=default, docs=docs)
            action = parser.add_argument(
                '-b', '--blah', action='store_true', help=default, docs=docs)
            arg_group = parser.add_argument_group('fa', description=default, docs=docs)
            mut_arg_group = parser.add_mutually_exclusive_group()
            mut_action = mut_arg_group.add_argument(
                '-f', '--fee', action='store_true', help=default, docs=docs)

            self.assertEqual(getattr(parser._subparsers, 'description', None), expected_txt)
            self.assertEqual(getattr(subparser, 'description', None), expected_txt)
            self.assertEqual(getattr(action, 'help', None), expected_txt)
            self.assertEqual(getattr(arg_group, 'description', None), expected_txt)
            self.assertEqual(getattr(mut_action, 'help', None), expected_txt)

        # list/tuple-based docs
        arghparse._generate_docs = True
        docs = 'foo bar'
        parser = argparse.ArgumentParser()
        list_action = parser.add_argument(
            '-b', '--blah', action='store_true', help=default, docs=list(docs.split()))
        tuple_action = parser.add_argument(
            '-c', '--cat', action='store_true', help=default, docs=tuple(docs.split()))
        self.assertEqual(getattr(list_action, 'help', None), 'foo\nbar')
        self.assertEqual(getattr(tuple_action, 'help', None), 'foo\nbar')


class ArgparseOptionsTest(TestCase):

    def setUp(self):
        self.parser = argparse_helpers.mangle_parser(arghparse.ArgumentParser())

    def test_debug(self):
        namespace = self.parser.parse_args(["--debug"])
        self.assertTrue(namespace.debug)
        namespace = self.parser.parse_args([])
        self.assertFalse(namespace.debug)

    def test_debug_disabled(self):
        # ensure the option isn't there if disabled.
        parser = argparse_helpers.mangle_parser(arghparse.ArgumentParser(debug=False))
        namespace = parser.parse_args([])
        self.assertFalse(hasattr(namespace, 'debug'))

    def test_bool_type(self):
        self.parser.add_argument(
            "--testing", action=arghparse.StoreBool, default=None)

        for raw_val in ("n", "no", "false"):
            for allowed in (raw_val.upper(), raw_val.lower()):
                namespace = self.parser.parse_args(['--testing=' + allowed])
                self.assertEqual(
                    namespace.testing, False,
                    msg="for --testing=%s, got %r, expected False" %
                        (allowed, namespace.testing))

        for raw_val in ("y", "yes", "true"):
            for allowed in (raw_val.upper(), raw_val.lower()):
                namespace = self.parser.parse_args(['--testing=' + allowed])
                self.assertEqual(
                    namespace.testing, True,
                    msg="for --testing=%s, got %r, expected False" %
                        (allowed, namespace.testing))

        try:
            self.parser.parse_args(["--testing=invalid"])
        except argparse_helpers.Error:
            pass
        else:
            self.fail("no error message thrown for --testing=invalid")

    def test_extend_comma_action(self):
        self.parser.add_argument('--testing', action='extend_comma')
        self.parser.add_argument('--testing-nargs', nargs='+', action='extend_comma')

        test_values = (
            ('', []),
            (',', []),
            (',,', []),
            ('a', ['a']),
            ('a,b,-c', ['a', 'b', '-c']),
        )
        for raw_val, expected in test_values:
            namespace = self.parser.parse_args([
                '--testing=' + raw_val,
                '--testing-nargs', raw_val, raw_val,
                ])
            self.assertEqual(namespace.testing, expected)
            self.assertEqual(namespace.testing_nargs, expected * 2)

    def test_extend_comma_toggle_action(self):
        self.parser.add_argument('--testing', action='extend_comma_toggle')
        self.parser.add_argument('--testing-nargs', nargs='+', action='extend_comma_toggle')

        test_values = (
            ('', ([], [])),
            (',', ([], [])),
            (',,', ([], [])),
            ('a', ([], ['a'])),
            ('a,-b,-c,d', (['b', 'c'], ['a', 'd'])),
        )
        for raw_val, expected in test_values:
            namespace = self.parser.parse_args([
                '--testing=' + raw_val,
                '--testing-nargs', raw_val, raw_val,
                ])
            self.assertEqual(namespace.testing, expected)
            self.assertEqual(namespace.testing_nargs, (expected[0] * 2, expected[1] * 2))

        # start with negated arg
        namespace = self.parser.parse_args(['--testing=-a'])
        self.assertEqual(namespace.testing, (['a'], []))

    def test_existent_path(self):
        self.parser.add_argument('--path', type=arghparse.existent_path)

        # nonexistent path arg raises an error
        with self.assertRaises(argparse_helpers.Error):
            self.parser.parse_args(['--path=/path/to/nowhere'])

        dir = tempfile.mkdtemp()
        # random OS/FS issues raise errors
        with mock.patch('snakeoil.osutils.abspath') as abspath:
            abspath.side_effect = OSError(19, 'Random OS error')
            with self.assertRaises(argparse_helpers.Error):
                self.parser.parse_args(['--path=%s' % dir])

        # regular usage
        namespace = self.parser.parse_args(['--path=%s' % dir])
        self.assertEqual(namespace.path, dir)
        os.rmdir(dir)


class NamespaceTest(TestCase):

    def setUp(self):
        self.parser = argparse_helpers.mangle_parser(arghparse.ArgumentParser())

    def test_pop(self):
        self.parser.set_defaults(test=True)
        namespace = self.parser.parse_args([])
        self.assertTrue(namespace.pop('test'))

        # re-popping raises an exception since the attr has been removed
        with self.assertRaises(AttributeError):
            namespace.pop('test')

        # popping a nonexistent attr with a fallback returns the fallback
        self.assertEqual(namespace.pop('nonexistent', 'foo'), 'foo')

    def test_collapse_delayed(self):
        def _delayed_val(namespace, attr, val):
            setattr(namespace, attr, val)
        self.parser.set_defaults(delayed=arghparse.DelayedValue(partial(_delayed_val, val=42)))
        namespace = self.parser.parse_args([])
        self.assertEqual(namespace.delayed, 42)