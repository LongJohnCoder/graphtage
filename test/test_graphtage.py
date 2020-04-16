from io import StringIO
from unittest import TestCase

import graphtage

from graphtage.printer import Printer


class TestGraphtage(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.small_from = graphtage.build_tree({
            "test": "foo",
            "baz": 1
        })
        cls.small_to = graphtage.build_tree({
            "test": "bar",
            "baz": 2
        })
        cls.list_from = graphtage.build_tree([0, 1, 2, 3, 4, 5])
        cls.list_to = graphtage.build_tree([1, 2, 3, 4, 5])

    def test_string_diff_printing(self):
        s1 = graphtage.StringNode("abcdef")
        s2 = graphtage.StringNode("azced")
        diff = graphtage.Diff(
            s1,
            s2,
            (graphtage.Match(s1, s2, graphtage.levenshtein_distance(s1.object, s2.object)),)
        )
        out_stream = StringIO()
        p = Printer(ansi_color=True, out_stream=out_stream)
        diff.print(p)
        self.assertEqual(diff.cost(), 3)
        self.assertEqual('"\x1b[37m\x1b[41m\x1b[1m\x1b[0m\x1b[49m\x1b[39m\x1b[37m\x1b[42m\x1b[1m\x1b[0m\x1b[49m\x1b[39ma\x1b[37m\x1b[41m\x1b[1mb̶\x1b[0m\x1b[49m\x1b[39m\x1b[37m\x1b[42m\x1b[1mz̟\x1b[0m\x1b[49m\x1b[39mc\x1b[37m\x1b[41m\x1b[1m\x1b[0m\x1b[49m\x1b[39m\x1b[37m\x1b[42m\x1b[1m\x1b[0m\x1b[49m\x1b[39m\x1b[37m\x1b[41m\x1b[1md̶\x1b[0m\x1b[49m\x1b[39m\x1b[37m\x1b[42m\x1b[1m\x1b[0m\x1b[49m\x1b[39me\x1b[37m\x1b[41m\x1b[1mf̶\x1b[0m\x1b[49m\x1b[39m\x1b[37m\x1b[42m\x1b[1md̟\x1b[0m\x1b[49m\x1b[39m"\n', out_stream.getvalue())

    def test_string_diff_remove_insert_reordering(self):
        s1 = graphtage.StringNode('abcdefg')
        s2 = graphtage.StringNode('abhijfg')
        diff = graphtage.Diff(
            s1,
            s2,
            (graphtage.Match(s1, s2, graphtage.levenshtein_distance(s1.object, s2.object)),)
        )
        out_stream = StringIO()
        p = Printer(ansi_color=True, out_stream=out_stream)
        diff.print(p)
        self.assertEqual('"\x1b[37m\x1b[41m\x1b[1m\x1b[0m\x1b[49m\x1b[39m\x1b[37m\x1b[42m\x1b[1m\x1b[0m\x1b[49m\x1b[39ma\x1b[37m\x1b[41m\x1b[1m\x1b[0m\x1b[49m\x1b[39m\x1b[37m\x1b[42m\x1b[1m\x1b[0m\x1b[49m\x1b[39mb\x1b[37m\x1b[41m\x1b[1mc̶d̶e̶\x1b[0m\x1b[49m\x1b[39m\x1b[37m\x1b[42m\x1b[1mh̟i̟j̟\x1b[0m\x1b[49m\x1b[39mf\x1b[37m\x1b[41m\x1b[1m\x1b[0m\x1b[49m\x1b[39m\x1b[37m\x1b[42m\x1b[1m\x1b[0m\x1b[49m\x1b[39mg\x1b[37m\x1b[41m\x1b[1m\x1b[0m\x1b[49m\x1b[39m\x1b[37m\x1b[42m\x1b[1m\x1b[0m\x1b[49m\x1b[39m"\n', out_stream.getvalue())

    def test_small_diff(self):
        diff = graphtage.diff(self.small_from, self.small_to)
        has_test_match = False
        has_baz_match = False
        for edit in diff:
            if edit.bounds().upper_bound > 0:
                self.assertIsInstance(edit, graphtage.Match)
                if isinstance(edit.from_node, graphtage.StringNode):
                    self.assertIsInstance(edit.to_node, graphtage.StringNode)
                    self.assertEqual(edit.from_node.object, 'foo')
                    self.assertEqual(edit.to_node.object, 'bar')
                    self.assertEqual(edit.bounds().upper_bound, 3)
                    self.assertFalse(has_test_match)
                    has_test_match = True
                elif isinstance(edit.from_node, graphtage.IntegerNode):
                    self.assertIsInstance(edit.to_node, graphtage.IntegerNode)
                    self.assertEqual(edit.from_node.object, 1)
                    self.assertEqual(edit.to_node.object, 2)
                    self.assertEqual(edit.bounds().upper_bound, 1)
                    self.assertFalse(has_baz_match)
                    has_baz_match = True
                else:
                    self.fail()
        self.assertTrue(has_test_match)
        self.assertTrue(has_baz_match)

    def test_list_diff(self):
        diff = graphtage.diff(self.list_from, self.list_to)
        for edit in diff:
            if edit.bounds().upper_bound > 0:
                self.assertIsInstance(edit, graphtage.Remove)
                self.assertIsInstance(edit.from_node, graphtage.IntegerNode)
                self.assertEqual(edit.from_node.object, 0)
                self.assertIsInstance(edit.to_node, graphtage.ListNode)
                self.assertIs(edit.to_node, self.list_from)
            else:
                self.assertIsInstance(edit, graphtage.Match)
