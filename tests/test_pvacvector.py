import unittest
import tempfile
import py_compile
import shutil
from filecmp import cmp
import os
import sys
import re
from subprocess import PIPE
from subprocess import run as subprocess_run
from tools.pvacvector import *
import unittest.mock
from mock import patch
from .test_utils import *

def make_response(data, path, test_name):
    filename = 'response_%s_%s_%s_%s.tsv' % (data['allele'], data['length'], data['method'], test_name)
    reader = open(os.path.join(
        path,
        filename
    ), mode='r')
    response_obj = lambda :None
    response_obj.status_code = 200
    response_obj.text = reader.read()
    reader.close()
    return response_obj

def test_data_directory():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
    return os.path.join(base_dir, 'tests', 'test_data', 'pvacvector')

#python -m unittest tests/test_pvacvector.py
class TestPvacvector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
        cls.python = sys.executable
        cls.executable = os.path.join(cls.base_dir, 'tools', 'pvacvector', 'run.py')
        cls.test_run_name = 'test_pvacvector_produces_expected_output'
        cls.test_data_dir = test_data_directory()
        cls.test_data_temp_dir = os.path.join(cls.test_data_dir, 'tmp')
        cls.input_tsv = os.path.join(cls.test_data_dir, 'input_parse_test_input.tsv')
        cls.input_vcf = os.path.join(cls.test_data_dir, 'input_parse_test_input.vcf')
        cls.input_file = os.path.join(cls.test_data_dir, 'Test.vector.results.input.fa')
        cls.method = 'NetMHC'
        cls.keep_tmp = 'True'
        cls.allele = 'H-2-Kb'
        cls.epitope_length = '8'
        cls.input_n_mer = '25'

    def test_run_compiles(self):
        self.assertTrue(py_compile.compile(self.executable))

    def test_pvacvector_compiles(self):
        compiled_path = py_compile.compile(os.path.join(
            self.base_dir,
            'tools',
            'pvacvector',
            'main.py'
        ))
        self.assertTrue(compiled_path)

    def test_pvacvector_commands(self):
        pvac_script_path = os.path.join(
            self.base_dir,
            'tools',
            'pvacvector',
            'main.py'
        )
        usage_search = re.compile(r"usage: ")
        for command in [
            "run",
            ]:
            result = subprocess_run([
                sys.executable,
                pvac_script_path,
                command,
                '-h'
            ], shell=False, stdout=PIPE)
            self.assertFalse(result.returncode)
            self.assertRegex(result.stdout.decode(), usage_search)

    def test_pvacvector_fa_input_runs_and_produces_expected_output(self):
        with patch('requests.post', unittest.mock.Mock(side_effect = lambda url, data: make_response(
            data,
            test_data_directory(),
            'fa_input',
        ))) as mock_request:
            output_dir = tempfile.TemporaryDirectory()

            run.main([
                self.input_file,
                self.test_run_name,
                self.allele,
                self.method,
                output_dir.name,
                '-e', self.epitope_length,
                '-n', self.input_n_mer,
                '-k'
            ])

            #vaccine design algorithm producing correct output with fasta input
            self.assertTrue(cmp(
                os.path.join(output_dir.name, self.test_run_name + '_results.fa'),
                os.path.join(self.test_data_dir, "Test.vector.results.output.fa")
            ))

            image_out = os.path.join(output_dir.name, 'vector.jpg')
            #vaccine visualization producing image
            self.assertTrue(os.path.exists(image_out))
            self.assertTrue(os.stat(image_out).st_size > 0)

            output_dir.cleanup()

    def test_pvacvector_generate_fa_runs_and_produces_expected_output(self):
        with patch('requests.post', unittest.mock.Mock(side_effect = lambda url, data, files=None: make_response(
            data,
            test_data_directory(),
            'generate_fa',
        ))) as mock_request:
            output_dir = tempfile.TemporaryDirectory()

            run.main([
                self.input_tsv,
                self.test_run_name,
                self.allele,
                self.method,
                output_dir.name,
                '-v', self.input_vcf,
                '-e', self.epitope_length,
                '-n', self.input_n_mer,
                '-k',
                '-b', '50',
            ])

            #conversion from vcf to fasta file producing correct output, input file for vaccine design algorithm
            self.assertTrue(compare(
                    os.path.join(output_dir.name, "vector_input.fa"),
                    os.path.join(self.test_data_dir, "input_parse_test_output.fa")
                    ))

            image_out = os.path.join(output_dir.name, 'vector.jpg')
            #vaccine visualization producing image
            self.assertTrue(os.path.exists(image_out))
            self.assertTrue(os.stat(image_out).st_size > 0)

            output_dir.cleanup()
