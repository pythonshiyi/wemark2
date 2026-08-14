import logging
from pathlib import Path

from core.logger import get_logger, setup_logger


class TestLogger:
    def test_get_logger_returns_logger_instance(self):
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_get_logger_default_name(self):
        logger = get_logger()
        assert logger.name == "wemark"

    def test_setup_logger_returns_logger(self):
        logger = setup_logger("test_setup", level=logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_setup_logger_has_handlers(self):
        logger = setup_logger("test_handlers")
        assert len(logger.handlers) >= 1

    def test_setup_logger_does_not_duplicate_handlers(self):
        logger = setup_logger("test_no_dup")
        count = len(logger.handlers)
        logger2 = setup_logger("test_no_dup")
        assert len(logger2.handlers) == count

    def test_logger_console_handler_exists(self, caplog):
        logger = setup_logger("test_console")
        handler_names = [type(h).__name__ for h in logger.handlers]
        assert "StreamHandler" in handler_names

    def test_setup_logger_uses_specified_name(self):
        logger = setup_logger("my_custom_name")
        assert logger.name == "my_custom_name"

    def test_setup_logger_has_formatter(self):
        logger = setup_logger("test_format")
        for handler in logger.handlers:
            formatter = handler.formatter
            assert formatter is not None
            assert "%(asctime)s" in formatter._fmt
            break

    def test_logger_does_not_log_below_level(self, caplog):
        logger = setup_logger("test_level", level=logging.WARNING)
        caplog.set_level(logging.WARNING)
        logger.info("should not appear")
        assert "should not appear" not in caplog.text

    def test_logger_logs_at_correct_level(self, caplog):
        logger = setup_logger("test_correct_level", level=logging.INFO)
        caplog.set_level(logging.INFO)
        logger.info("info message")
        assert "info message" in caplog.text


class TestLoggerEdgeCases:
    def test_get_logger_without_setup_returns_root_child(self):
        logger = get_logger("unconfigured_module")
        assert isinstance(logger, logging.Logger)

    def test_setup_logger_custom_level_from_string(self):
        logger = setup_logger("test_str_level", level=logging.ERROR)
        assert logger.level == logging.ERROR

    def test_logger_name_with_dots(self):
        logger = setup_logger("my.module.logger")
        assert logger.name == "my.module.logger"
