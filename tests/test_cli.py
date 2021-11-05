import unittest
from unittest import mock

from taskcat._cli import (
    _print_upgrade_msg,
    _setup_logging,
    _welcome,
    check_for_update,
    main,
)
from taskcat.exceptions import TaskCatException


class TestCli(unittest.TestCase):
    @mock.patch("taskcat._cli.LOG.error")
    @mock.patch("taskcat._cli._welcome", autospec=True)
    @mock.patch("taskcat._cli.get_installed_version", autospec=True)
    @mock.patch("taskcat._cli_core.CliCore")
    @mock.patch("taskcat._cli._setup_logging", autospec=True)
    @mock.patch("taskcat._common_utils.exit_with_code", autospec=True)
    @mock.patch("sys.argv", autospec=True)
    @mock.patch("signal.signal", autospec=True)
    def test_main(
        self, m_signal, m_argv, m_exit, m_log_setup, m_cli, m_ver, m_welcome, m_error
    ):
        mock_clicore_instantiation = mock.MagicMock()
        mock_clicore_instantiation.parsed_args = mock.MagicMock()
        m_cli.return_value = mock_clicore_instantiation
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

    @mock.patch("taskcat._cli.get_distribution", autospec=True)
    def test_check_for_update(self, mock_get_distribution):
        mock_get_distribution.return_value.version = "0.1.0"
        check_for_update()
        self.assertEqual(mock_get_distribution.call_count, 1)
        mock_get_distribution.side_effect = TypeError("test")
        check_for_update()
        self.assertEqual(mock_get_distribution.call_count, 2)

    @mock.patch("taskcat._cli.LOG", autospec=True)
    def test__print_upgrade_msg(self, mock_log):
        _print_upgrade_msg("0.1.0", "0.0.1")
        mock_log.warning.assert_called_once()
        mock_log.info.assert_called()

    @mock.patch("taskcat._cli.get_pip_version", autospec=True)
    @mock.patch("taskcat._cli.get_installed_version", autospec=True)
    @mock.patch("taskcat._cli.LOG", autospec=True)
    @mock.patch("taskcat._cli._print_upgrade_msg")
    def test_check_for_update_ver_is_sub_of_current(
        self, mock_upg_msg, mock_log, mock_get_installed, mock_get_pip
    ):
        # already latest
        mock_get_installed.return_value = "0.1.0"
        mock_get_pip.return_value = "0.1.0"
        check_for_update()
        mock_log.info.assert_called()
        mock_upg_msg.assert_not_called()
        # upgrade available
        mock_get_pip.return_value = "0.1.1"
        check_for_update()
        mock_upg_msg.assert_called_once()

    @mock.patch("taskcat._cli.check_for_update", autospec=True)
    @mock.patch("taskcat._cli.LOG", autospec=True)
    def test__welcome(self, mock_log, mock_check_for_update):
        _welcome()
        self.assertTrue(mock_check_for_update.call_count, 1)
        mock_log.info.assert_called_once()

        # should pass without raising if something unexpected happens
        mock_check_for_update.side_effect = TypeError("something")
        _welcome()
        self.assertTrue(mock_check_for_update.call_count, 2)
        mock_log.warning.assert_called_once()
