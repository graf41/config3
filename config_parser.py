#!/usr/bin/env python3
import argparse
import re
import sys
import yaml

class ConfigParserError(Exception):
    """Класс для обработки ошибок парсера."""
    def __init__(self, message, line_num):
        super().__init__(f"Ошибка на строке {line_num}: {message}")
        self.line_num = line_num

class ConfigParser:
    def __init__(self, lines):
        self.lines = lines
        self.constants = {}
        self.line_num = 0

    def parse(self):
        result = {}
        while self.line_num < len(self.lines):
            line = self.lines[self.line_num].strip()
            print(f"DEBUG: Обработка строки {self.line_num + 1}: '{line}'")  # Отладочный вывод
            if not line or line.startswith('#'):  # Пропуск пустых строк и комментариев
                self.line_num += 1
                continue
            if '->' in line and line.endswith(';'):  # Объявление константы
                self._parse_constant_declaration(line)
            elif line.startswith('begin'):  # Начало словаря
                dict_name, dict_content = self._parse_dictionary()
                if dict_name in result:
                    self._raise_error(f"Дублирование имени словаря '{dict_name}'.")
                result[dict_name] = dict_content
            else:
                print(f"DEBUG: Неопознанная строка: '{line}'")  # Отладка
                self._raise_error("Неизвестная конструкция.")
        return result

    def _parse_constant_declaration(self, line):
        print(f"DEBUG: Разбор строки {self.line_num + 1}: '{line}'")  # Отладочный вывод
        # Регулярное выражение для объявления констант
        match = re.match(r'^\s*(.+?)\s*->\s*([a-zA-Z][_a-zA-Z0-9]*)\s*;\s*(#.*)?$', line)
        if not match:
            self._raise_error("Некорректное объявление константы.")
        value_str, name, comment = match.groups()
        print(f"DEBUG: Значение = '{value_str.strip()}', Имя = '{name.strip()}', Комментарий = '{comment.strip() if comment else ''}'")  # Отладка
        value = self._parse_value(value_str.strip())
        self.constants[name] = value
        self.line_num += 1

    def _parse_dictionary(self):
        line = self._current_line()
        match = re.match(r'^begin\s+([a-zA-Z][_a-zA-Z0-9]*)\s*$', line)
        if not match:
            self._raise_error("Некорректное объявление словаря.")
        dict_name = match.group(1)
        dict_content = {}
        self.line_num += 1
        while self.line_num < len(self.lines):
            line = self._current_line().strip()
            if line.startswith('end'):
                self.line_num += 1
                return dict_name, dict_content
            if line.startswith('begin'):
                # Обработка вложенного словаря
                nested_dict_name, nested_dict_content = self._parse_dictionary()
                if nested_dict_name in dict_content:
                    self._raise_error(f"Дублирование ключа '{nested_dict_name}' в словаре '{dict_name}'.")
                dict_content[nested_dict_name] = nested_dict_content
                continue
            if not line.endswith(';'):
                self._raise_error("Ожидался ';' в конце строки.")
            match = re.match(r'^([a-zA-Z][_a-zA-Z0-9]*)\s*:=\s*(.+);$', line)
            if not match:
                self._raise_error("Некорректное присваивание в словаре.")
            key, value_str = match.groups()
            if key in dict_content:
                self._raise_error(f"Дублирование ключа '{key}' в словаре '{dict_name}'.")
            value = self._parse_value(value_str.strip())
            dict_content[key] = value
            self.line_num += 1
        self._raise_error("Ожидался 'end;' для закрытия словаря.")

    def _current_line(self):
        return self.lines[self.line_num]

    def _parse_value(self, value_str):
        # Обработка строк
        if value_str.startswith('"') and value_str.endswith('"'):
            return value_str[1:-1]
        # Обработка чисел
        elif re.match(r'^-?\d+(\.\d+)?$', value_str):
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        # Обработка массивов
        elif value_str.startswith('{') and value_str.endswith('}'):
            return self._parse_array(value_str[1:-1].strip())
        # Обработка выражений
        elif value_str.startswith('@[') and value_str.endswith(']'):
            return self._evaluate_expression(value_str[2:-1].strip())
        # Обработка констант
        elif value_str in self.constants:
            return self.constants[value_str]
        # Некорректное значение
        self._raise_error(f"Неизвестное значение: '{value_str}'")

    def _parse_array(self, array_str):
        if not array_str:
            return []
        # Используем регулярное выражение для корректного разбора элементов массива
        # Элементы могут быть строками в кавычках или числами
        pattern = r'"[^"]*"|-?\d+(?:\.\d+)?'
        elements = re.findall(pattern, array_str)
        if not elements:
            self._raise_error("Некорректный синтаксис массива.")
        return [self._parse_value(elem.strip()) for elem in elements]

    def _evaluate_expression(self, expr_str):
        tokens = expr_str.split()
        stack = []
        for token in tokens:
            # Если это число
            if re.match(r'^-?\d+(\.\d+)?$', token):
                if '.' in token:
                    stack.append(float(token))
                else:
                    stack.append(int(token))
            # Если это константа
            elif token in self.constants:
                stack.append(self.constants[token])
            # Если это оператор
            elif token in ('+', '-', '*', '/', 'mod()'):
                if len(stack) < 2:
                    self._raise_error("Недостаточно операндов для операции.")
                b = stack.pop()
                a = stack.pop()
                result = self._apply_operator(a, b, token)
                stack.append(result)
            else:
                self._raise_error(f"Неизвестный токен '{token}' в выражении.")
        # После обработки выражения в стеке должно остаться ровно одно значение
        if len(stack) != 1:
            self._raise_error("Некорректное выражение.")
        return stack[0]

    def _apply_operator(self, a, b, operator):
        try:
            if operator == '+':
                return a + b
            elif operator == '-':
                return a - b
            elif operator == '*':
                return a * b
            elif operator == '/':
                if b == 0:
                    self._raise_error("Деление на ноль.")
                return a / b
            elif operator == 'mod()':
                if not isinstance(a, int) or not isinstance(b, int):
                    self._raise_error("Оператор 'mod()' применяется только к целым числам.")
                if b == 0:
                    self._raise_error("Деление на ноль в 'mod()'.")
                return a % b
        except Exception as e:
            self._raise_error(f"Ошибка при применении оператора '{operator}': {e}")

    def _raise_error(self, message):
        raise ConfigParserError(message, self.line_num + 1)

def main():
    parser = argparse.ArgumentParser(description='Инструмент преобразования конфигурационного файла в YAML.')
    parser.add_argument('-i', '--input', required=True, help='Путь к входному конфигурационному файлу.')
    parser.add_argument('-o', '--output', required=True, help='Путь к выходному YAML файлу.')
    args = parser.parse_args()

    try:
        with open(args.input, 'r', encoding='utf-8') as infile:
            lines = infile.readlines()
    except FileNotFoundError:
        print(f"Ошибка: Файл '{args.input}' не найден.")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при чтении файла '{args.input}': {e}")
        sys.exit(1)

    config_parser = ConfigParser(lines)
    try:
        yaml_data = config_parser.parse()
    except ConfigParserError as e:
        print(e)
        sys.exit(1)

    try:
        with open(args.output, 'w', encoding='utf-8') as outfile:
            yaml.dump(yaml_data, outfile, allow_unicode=True, sort_keys=False, default_flow_style=False)
        print(f"Успешно преобразовано в '{args.output}'.")
    except Exception as e:
        print(f"Ошибка при записи в файл '{args.output}': {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
