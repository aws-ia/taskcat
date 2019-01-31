from __future__ import print_function

import mock
import unittest

from taskcat.exceptions import TaskCatException
from taskcat.common_utils import param_list_to_dict
from taskcat.common_utils import get_file_list
    
def execute(exclusions, dirs):
    os_walk_mock = [
        ('./foo', ('.git', 'baz'), ('.gitignore', 'bar')),
        ('./foo/.git', (), ('file1', 'file2')),
        ('./foo/baz', (), ('a.js', 'b.yaml', '.hidden', 'c.txt', 'd.js'))
    ]
    with mock.patch('os.walk') as mockwalk:
        mockwalk.return_value = os_walk_mock
        with mock.patch('os.path.isdir') as mockisdir:
            mockisdir.return_value = dirs
            result = get_file_list('.', exclusions)
            result.sort()
            return result


class TestCfnLogTools(unittest.TestCase):

    def test_get_param_includes(self):
        bad_testcases = [
            {},
            [[]],
            [{}]
        ]
        for bad in bad_testcases:
            with self.assertRaises(TaskCatException):
                param_list_to_dict(bad)

class TestGetFileList(unittest.TestCase):

    def test_get_exclude_hidden_files(self):
        result = execute(['*/.*'], [False])
        expected = ['./foo/bar', './foo/baz/a.js', './foo/baz/b.yaml', './foo/baz/c.txt', './foo/baz/d.js']
        self.assertEqual(result, expected)

    def test_get_exclude_js_files(self):
        result = execute(['*.js'], [False])
        expected = ['./foo/.git/file1', './foo/.git/file2', './foo/.gitignore', './foo/bar', './foo/baz/.hidden', './foo/baz/b.yaml', './foo/baz/c.txt']
        self.assertEqual(result, expected)

    def test_get_exclude_hidden_and_js_files(self):
        result = execute(['*.js', '*/.*'], [False, False])
        expected = ['./foo/bar', './foo/baz/b.yaml', './foo/baz/c.txt']
        self.assertEqual(result, expected)

    def test_get_exclude_unnormalized_folder_and_hidden_files(self):
        result = execute(['foo/baz', '*/.*'], [True, False])
        expected = ['./foo/bar']
        self.assertEqual(result, expected)

    def test_get_exclude_unnormalized_folder_with_wildcard_and_hidden_files(self):
        result = execute(['foo/baz/*', '*/.*'], [False, False])
        expected = ['./foo/bar']
        self.assertEqual(result, expected)

    def test_get_exclude_normalized_folder_and_hidden_files(self):
        result = execute(['./foo/baz', '*/.*'], [True, False])
        expected = ['./foo/bar']
        self.assertEqual(result, expected)

    def test_get_exclude_normalized_folder_with_wildcard_and_hidden_files(self):
        result = execute(['./foo/baz/*', '*/.*'], [True, False])
        expected = ['./foo/bar']
        self.assertEqual(result, expected)

    def test_get_exclude_folder_and_js_files(self):
        result = execute(['foo/.git*', '*.js'], [True, False])
        expected = ['./foo/bar', './foo/baz/.hidden', './foo/baz/b.yaml', './foo/baz/c.txt']
        self.assertEqual(result, expected)
