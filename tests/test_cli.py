import unittest
import mock

from taskcat._cli import main, _setup_logging, check_for_update
from taskcat.exceptions import TaskCatException


class TestCli(unittest.TestCase):
    @mock.patch("taskcat._cli.LOG.error")
    @mock.patch("taskcat._cli._welcome", autospec=True)
    @mock.patch("taskcat._cli.get_installed_version", autospec=True)
    @mock.patch("taskcat._cli_core.CliCore", autospec=True)
    @mock.patch("taskcat._cli._setup_logging", autospec=True)
    @mock.patch("taskcat._common_utils.exit_with_code", autospec=True)
    @mock.patch("sys.argv", autospec=True)
    @mock.patch("signal.signal", autospec=True)
    def test_main(
        self, m_signal, m_argv, m_exit, m_log_setup, m_cli, m_ver, m_welcome, m_error
    ):
        main(cli_core_class=m_cli, exit_func=m_exit)
        self.assertEqual(True, m_signal.called)
        self.assertEqual(True, m_log_setup.called)
        self.assertEqual(True, m_welcome.called)
        self.assertEqual(True, m_ver.called)
        self.assertEqual(False, m_exit.called)
        m_cli.assert_called_once()
        m_error.assert_not_called()

        m_welcome.side_effect = TaskCatException("an error")
        main(cli_core_class=m_cli, exit_func=m_exit)
        m_error.assert_called_once_with("an error", exc_info=False)
        m_error.assert_called_once()

        m_welcome.side_effect = None
        m_error.reset_mock()
        m_cli.side_effect = TypeError("another error")
        main(cli_core_class=m_cli, exit_func=m_exit)
        m_error.assert_called_once_with(
            "%s %s", "TypeError", "another error", exc_info=False
        )
        m_error.assert_called_once()

    @mock.patch("taskcat._cli.LOG.setLevel")
    @mock.patch("taskcat._common_utils.exit_with_code", autospec=True)
    def test_setup_logging(self, m_exit, m_setLevel):
        _setup_logging([], exit_func=m_exit)
        m_setLevel.assert_called_once_with("INFO")
        self.assertEqual(False, m_exit.called)
        for debug_flag in ["-d", "--debug"]:
            m_setLevel.reset_mock()
            _setup_logging([debug_flag], exit_func=m_exit)
            m_setLevel.assert_called_once_with("DEBUG")
            self.assertEqual(False, m_exit.called)
        for quiet_flag in ["-q", "--quiet"]:
            m_setLevel.reset_mock()
            _setup_logging([quiet_flag], exit_func=m_exit)
            m_setLevel.assert_called_once_with("ERROR")
            self.assertEqual(False, m_exit.called)
        m_setLevel.reset_mock()
        _setup_logging(["-d", "-q"], exit_func=m_exit)
        self.assertEqual(True, m_exit.called)

    @mock.patch("taskcat._cli.LOG.info")
    @mock.patch("taskcat._cli.LOG.warning")
    def test_check_for_update(self, m_warning, m_info):
        check_for_update()
        m_warning.assert_called_once_with("Unable to get version info!!, continuing")
        with mock.patch("taskcat._cli.get_pip_version") as m_curver:
            m_curver.return_value = "0.0.1"
            check_for_update()
            m_curver.assert_called_once()
