import unittest
from config_parser import ConfigParser, ConfigParserError

class TestConfigParser(unittest.TestCase):
    def setUp(self):
        self.parser = ConfigParser([])

    def test_constants(self):
        lines = [
            '20 -> max_connections;',
            '"localhost" -> server_host;',
            '@[10 5 +] -> calculated_value;',
        ]
        self.parser.lines = lines
        result = self.parser.parse()
        self.assertEqual(self.parser.constants['max_connections'], 20)
        self.assertEqual(self.parser.constants['server_host'], 'localhost')
        self.assertEqual(self.parser.constants['calculated_value'], 15)

    def test_simple_dictionary(self):
        lines = [
            '20 -> max_connections;',
            'begin server',
            'connections := max_connections;',
            'end;',
        ]
        self.parser.lines = lines
        result = self.parser.parse()
        expected = {
            'server': {
                'connections': 20
            }
        }
        self.assertEqual(result, expected)

    def test_nested_dictionary(self):
        lines = [
            'begin application',
            'name := "MyApp";',
            'begin settings',
            'theme := "dark";',
            'timeout := 30;',
            'end;',
            'end;',
        ]
        self.parser.lines = lines
        result = self.parser.parse()
        expected = {
            'application': {
                'name': 'MyApp',
                'settings': {
                    'theme': 'dark',
                    'timeout': 30
                }
            }
        }
        self.assertEqual(result, expected)

    def test_array_of_numbers(self):
        lines = [
            'begin data',
            'numbers := {1.2.3.4};',
            'end;',
        ]
        self.parser.lines = lines
        result = self.parser.parse()
        expected = {
            'data': {
                'numbers': [1, 2, 3, 4]
            }
        }
        self.assertEqual(result, expected)

    def test_array_of_strings_with_dots(self):
        lines = [
            'begin data',
            'hosts := {"host1.example.com"."host2.example.com"};',
            'end;',
        ]
        self.parser.lines = lines
        result = self.parser.parse()
        expected = {
            'data': {
                'hosts': ['host1.example.com', 'host2.example.com']
            }
        }
        self.assertEqual(result, expected)

    def test_expression_constant(self):
        lines = [
            '10 -> a;',
            '20 -> b;',
            '@[a b +] -> c;',
            'begin calc',
            'result := c;',
            'end;',
        ]
        self.parser.lines = lines
        result = self.parser.parse()
        expected = {
            'calc': {
                'result': 30
            }
        }
        self.assertEqual(result, expected)

    def test_nested_dictionary_in_users_conf(self):
        lines = [
            '"admin" -> default_user;',
            '"password123" -> default_password;',
            '@[60 30 /] -> session_timeout;',
            'begin users',
            'default_user := default_user;',
            'default_password := default_password;',
            'session_timeout := session_timeout;',
            'begin roles',
            'role1 := "admin";',
            'role2 := "editor";',
            'role3 := "viewer";',
            'end;',
            'end;',
        ]
        self.parser.lines = lines
        result = self.parser.parse()
        expected = {
            'users': {
                'default_user': 'admin',
                'default_password': 'password123',
                'session_timeout': 2.0,
                'roles': {
                    'role1': 'admin',
                    'role2': 'editor',
                    'role3': 'viewer'
                }
            }
        }
        self.assertEqual(result, expected)

    def test_invalid_constant_declaration(self):
        lines = [
            '20 max_connections;',  # Отсутствует '->'
        ]
        self.parser.lines = lines
        with self.assertRaises(ConfigParserError) as context:
            self.parser.parse()
        self.assertIn("Некорректное объявление константы.", str(context.exception))

    def test_invalid_dictionary_declaration(self):
        lines = [
            'begin1 server',  # Некорректное начало словаря
        ]
        self.parser.lines = lines
        with self.assertRaises(ConfigParserError) as context:
            self.parser.parse()
        self.assertIn("Некорректное объявление словаря.", str(context.exception))

    def test_missing_semicolon(self):
        lines = [
            '20 -> max_connections',
        ]
        self.parser.lines = lines
        with self.assertRaises(ConfigParserError) as context:
            self.parser.parse()
        self.assertIn("Некорректное объявление константы.", str(context.exception))

    def test_unknown_value(self):
        lines = [
            '@[unknown_operator] -> value;',
        ]
        self.parser.lines = lines
        with self.assertRaises(ConfigParserError) as context:
            self.parser.parse()
        self.assertIn("Неизвестное значение: '@[unknown_operator]'", str(context.exception))

    def test_incorrect_expression(self):
        lines = [
            '@[10 +] -> invalid_expr;',
        ]
        self.parser.lines = lines
        with self.assertRaises(ConfigParserError) as context:
            self.parser.parse()
        self.assertIn("Недостаточно операндов для операции.", str(context.exception))

    def test_nested_arrays(self):
        lines = [
            'begin complex',
            'values := {"value1"."value2"};',
            'numbers := {1.2.{3.4}};',  # Вложенные массивы не поддерживаются и должны вызвать ошибку
            'end;',
        ]
        self.parser.lines = lines
        with self.assertRaises(ConfigParserError) as context:
            self.parser.parse()
        self.assertIn("Неизвестное значение: '{3.4}'", str(context.exception))

    def test_mod_operation(self):
        lines = [
            '15 -> a;',
            '4 -> b;',
            '@[a b mod()] -> result;',  # 15 mod 4 = 3
            'begin math',
            'value := result;',
            'end;',
        ]
        self.parser.lines = lines
        result = self.parser.parse()
        expected = {
            'math': {
                'value': 3
            }
        }
        self.assertEqual(result, expected)

    def test_mod_operation_with_floats(self):
        lines = [
            '15.5 -> a;',
            '4 -> b;',
            '@[a b mod()] -> result;',  # Ошибка: mod() применён к float
            'begin math',
            'value := result;',
            'end;',
        ]
        self.parser.lines = lines
        with self.assertRaises(ConfigParserError) as context:
            self.parser.parse()
        self.assertIn("Оператор 'mod()' применяется только к целым числам.", str(context.exception))

if __name__ == '__main__':
    unittest.main()
