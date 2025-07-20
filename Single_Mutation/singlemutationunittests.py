import unittest
from unittest.mock import patch, mock_open, MagicMock, call
from single_mutation import (repair_pdb, make_mutation_list, file_key, get_mutation_names, rename_pdb_files, run_mutations, run_foldx_stability)

class TestFoldXWorkflow(unittest.TestCase):

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    @patch("subprocess.run")
    @patch("os.rename")
    def test_repair_pdb_success(self, mock_rename, mock_run, mock_file, mock_exists):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with patch("rich.console.Console.log"):
            repaired = repair_pdb("test")
        self.assertEqual(repaired, "test_Repair.pdb")

    @patch("os.path.exists", return_value=False)
    def test_repair_pdb_file_not_found(self, mock_exists):
        with self.assertRaises(FileNotFoundError):
            repair_pdb("test")

    @patch("builtins.open", new_callable=mock_open)
    def test_make_mutation_list(self, mock_file):
        residues = [("A", 469, "R")]
        make_mutation_list(residues)
        mock_file().writelines.assert_called()
        args = mock_file().writelines.call_args[0][0]
        self.assertTrue(any("RA469L" in line for line in args))

    def test_file_key_with_number(self):
        self.assertEqual(file_key("foo_123.pdb"), 123)

    def test_file_key_without_number(self):
        self.assertEqual(file_key("foo.pdb"), -1)

    @patch("builtins.open", new_callable=mock_open, read_data="A1B;\nB2C;\n")
    def test_get_mutation_names(self, mock_file):
        names = get_mutation_names("file.txt")
        self.assertEqual(names, ["A1B", "B2C"])

    @patch("glob.glob", return_value=["base_1.pdb", "base_2.pdb"])
    @patch("os.rename")
    def test_rename_pdb_files(self, mock_rename, mock_glob):
        rename_pdb_files("base_Repair.pdb", ["mutation1", "mutation2"])
        mock_rename.assert_has_calls([
            call('base_1.pdb', 'base_Repair_mutation1.pdb'),
            call('base_2.pdb', 'base_Repair_mutation2.pdb')
        ])
        assert mock_rename.call_count == 2

    @patch("os.rename")  # <-- Added to prevent FileNotFoundError
    @patch("single_mutation.run_foldx_command")
    @patch("builtins.open", new_callable=mock_open, read_data="RA468B;\nMA2C;\n")
    @patch("glob.glob", return_value=["base_Repair_1.pdb", "base_Repair_2.pdb"])
    def test_run_mutations(self, mock_glob, mock_file, mock_run_foldx_command, mock_rename):
        mock_result = MagicMock(returncode=0, stdout="ok", stderr="")
        mock_run_foldx_command.return_value = mock_result
        run_mutations("base_Repair.pdb")
        mock_run_foldx_command.assert_called()
        mock_rename.assert_has_calls([
            call('base_Repair_1.pdb', 'base_Repair_RA468B.pdb'),
            call('base_Repair_2.pdb', 'base_Repair_MA2C.pdb')
        ])
        assert mock_rename.call_count == 2

    @patch("glob.glob", return_value=["foo_Repair_1.pdb"])
    @patch("single_mutation.run_foldx_command")
    def test_run_foldx_stability_success(self, mock_run_foldx_command, mock_glob):
        mock_result = MagicMock(returncode=0)
        mock_run_foldx_command.return_value = mock_result
        result = run_foldx_stability("foo")
        self.assertTrue(result)

    @patch("glob.glob", return_value=[])
    def test_run_foldx_stability_no_files(self, mock_glob):
        result = run_foldx_stability("foo")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
