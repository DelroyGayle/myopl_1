#######################################
# IMPORTS
#######################################

import os
import math
import misc
import constants as c
from typing import Any, Self, Optional

#######################################
# ERRORS
#######################################


class Error:
    def __init__(
        self, pos_start: int, pos_end: int, error_name: str, details: str
    ) -> None:
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details

    def as_string(self) -> str:
        """Traceback Result"""
        result = f"{self.error_name}: {self.details}\n\n"
        result += (
            f"File {self.pos_start.filename}, "
            f"line {self.pos_start.linenum + 1}"
        )
        result += "\n\n" + misc.string_with_arrows(
            self.pos_start.filetext, self.pos_start, self.pos_end
        )
        return result


class IllegalCharError(Error):
    def __init__(self, pos_start: int, pos_end: int, details: str) -> None:
        super().__init__(pos_start, pos_end, "Illegal Character", details)


class ExpectedCharError(Error):
    def __init__(self, pos_start: int, pos_end: int, details: str) -> None:
        super().__init__(pos_start, pos_end, "Expected Character", details)


class InvalidSyntaxError(Error):
    def __init__(
        self, pos_start: int, pos_end: int, details: str = ""
    ) -> None:
        super().__init__(pos_start, pos_end, "Invalid Syntax", details)


class RTError(Error):
    def __init__(
        self, pos_start: int, pos_end: int, details: str, context: Any
    ) -> None:
        super().__init__(pos_start, pos_end, "Runtime Error", details)
        self.context = context

    def as_string(self) -> str:
        result = self.generate_traceback()
        result += f"{self.error_name}: {self.details}"
        result += "\n\n" + misc.string_with_arrows(
            self.pos_start.filetext, self.pos_start, self.pos_end
        )
        return result

    def generate_traceback(self) -> str:
        result = ""
        pos = self.pos_start
        context = self.context

        """
        Move up the context chain and build the 'result' string
        'context' will eventually result with the value None
        """
        while context:
            result = (
                f"  File {pos.filename}, line {str(pos.linenum + 1)}, "
                f"in {context.display_name}\n"
            ) + result
            pos = context.parent_entry_pos
            context = context.parent

        return "Traceback (most recent call last):\n" + result


#######################################
# POSITION
#######################################


class Position:
    def __init__(
        self,
        theindex: int,
        linenum: int,
        column: int,
        filename: str,
        filetext: str,
    ) -> None:
        self.theindex = theindex
        self.linenum = linenum
        self.column = column
        self.filename = filename
        self.filetext = filetext

    def advance(self, current_char: Optional[str] = None) -> Self:
        """Advance the position by 1"""
        self.theindex += 1
        self.column += 1

        if current_char == "\n":
            self.linenum += 1
            self.column = 0

        return self

    def copy(self) -> Self:
        return Position(
            self.theindex,
            self.linenum,
            self.column,
            self.filename,
            self.filetext,
        )


#######################################
# TOKENS
#######################################

TOKEN_TYPE_INT = "INT"
TOKEN_TYPE_FLOAT = "FLOAT"
TOKEN_TYPE_STRING = "STRING"
TOKEN_TYPE_IDENTIFIER = "IDENTIFIER"
TOKEN_TYPE_KEYWORD = "KEYWORD"
TOKEN_TYPE_PLUS = "PLUS"
TOKEN_TYPE_MINUS = "MINUS"
TOKEN_TYPE_MULTIPLY = "MULTIPLY"
TOKEN_TYPE_DIVIDE = "DIVIDE"
TOKEN_TYPE_MODULUS = "MODULUS"
TOKEN_TYPE_POWER = "POWER"
TOKEN_TYPE_ASSIGN = "ASSIGN"
TOKEN_TYPE_LPAREN = "LPAREN"
TOKEN_TYPE_RPAREN = "RPAREN"
TOKEN_TYPE_LSQUARE = "LSQUARE"
TOKEN_TYPE_RSQUARE = "RSQUARE"
TOKEN_TYPE_EQUAL_TO = "EQUAL_TO"
TOKEN_TYPE_NOT_EQUAL_TO = "NOT_EQUAL_TO"
TOKEN_TYPE_LESS_THAN = "LESS_THAN"
TOKEN_TYPE_GREATER_THAN = "GREATER_THAN"
TOKEN_TYPE_LESS_THAN_EQUAL_TO = "LESS_THAN_AND_EQUALTO"
TOKEN_TYPE_GREATER_THAN_EQUAL_TO = "GREATER_THAN_AND_EQUALTO"
TOKEN_TYPE_COMMA = "COMMA"
TOKEN_TYPE_ARROW = "ARROW"
TOKEN_TYPE_NEWLINE = "NEWLINE"
TOKEN_TYPE_EOF = "EOF"

COMPARISONS_TOKEN = (
    TOKEN_TYPE_EQUAL_TO,
    TOKEN_TYPE_NOT_EQUAL_TO,
    TOKEN_TYPE_LESS_THAN,
    TOKEN_TYPE_GREATER_THAN,
    TOKEN_TYPE_LESS_THAN_EQUAL_TO,
    TOKEN_TYPE_GREATER_THAN_EQUAL_TO,
)

KEYWORDS = [
    "VAR",
    "AND",
    "OR",
    "NOT",
    "IF",
    "ELIF",
    "ELSE",
    "FOR",
    "TO",
    "STEP",
    "WHILE",
    "FUN",
    "THEN",
    "END",
    "RETURN",
    "CONTINUE",
    "BREAK",
    "IMPORT",
]


class Token:
    def __init__(
        self,
        token_type: str,
        value: Optional[str] = None,
        pos_start: Optional[int] = None,
        pos_end: Optional[int] = None,
    ) -> None:
        self.type = token_type
        self.value = value

        if pos_start:
            self.pos_start = pos_start.copy()
            self.pos_end = pos_start.copy()
            self.pos_end.advance()

        if pos_end:
            self.pos_end = pos_end.copy()

    def matches(self, token_type: str, value: str) -> bool:
        """Does the token match the value?"""
        return self.type == token_type and self.value == value

    def __repr__(self) -> str:
        if self.value:
            return f"{self.type}:{self.value}"
        return f"{self.type}"


#######################################
# LEXER
#######################################


class Lexer:
    def __init__(self, filename: str, text: str) -> None:
        self.filename = filename
        self.text = text
        self.pos = Position(-1, 0, -1, filename, text)
        self.current_char = None
        self.advance()

    def advance(self) -> tuple:
        self.pos.advance(self.current_char)
        self.current_char = (
            self.text[self.pos.theindex]
            if self.pos.theindex < len(self.text)
            else None
        )

    def make_tokens(self) -> tuple:
        """Create a list of 'TOKENS'"""
        tokens = []

        while self.current_char is not None:
            if self.current_char in " \t":
                # Ignore spaces and tabs
                self.advance()
            elif self.current_char == "#":
                # Handle comments
                _, error = self.skip_comment()
                if error:
                    return [], error

            elif self.current_char in ";\n":
                tokens.append(Token(TOKEN_TYPE_NEWLINE, pos_start=self.pos))
                self.advance()
            elif self.current_char in c.DIGITS:
                result, error = self.make_number()
                if error:
                    return [], error

                tokens.append(result)

            elif self.current_char in c.LETTERS:
                tokens.append(self.make_identifier())
            elif self.current_char == '"':
                result, error = self.make_string()
                if error:
                    return [], error

                tokens.append(result)

            elif self.current_char == "+":
                tokens.append(Token(TOKEN_TYPE_PLUS, pos_start=self.pos))
                self.advance()
            elif self.current_char == "-":
                tokens.append(self.make_minus_or_arrow())
            elif self.current_char == "*":
                tokens.append(Token(TOKEN_TYPE_MULTIPLY, pos_start=self.pos))
                self.advance()
            elif self.current_char == "/":
                tokens.append(Token(TOKEN_TYPE_DIVIDE, pos_start=self.pos))
                self.advance()
            elif self.current_char == "%":
                tokens.append(Token(TOKEN_TYPE_MODULUS, pos_start=self.pos))
                self.advance()
            elif self.current_char == "^":
                tokens.append(Token(TOKEN_TYPE_POWER, pos_start=self.pos))
                self.advance()
            elif self.current_char == "(":
                tokens.append(Token(TOKEN_TYPE_LPAREN, pos_start=self.pos))
                self.advance()
            elif self.current_char == ")":
                tokens.append(Token(TOKEN_TYPE_RPAREN, pos_start=self.pos))
                self.advance()
            elif self.current_char == "[":
                tokens.append(Token(TOKEN_TYPE_LSQUARE, pos_start=self.pos))
                self.advance()
            elif self.current_char == "]":
                tokens.append(Token(TOKEN_TYPE_RSQUARE, pos_start=self.pos))
                self.advance()
            elif self.current_char == "!":
                token, error = self.make_not_equals()  # !=
                if error:
                    return [], error

                tokens.append(token)

            elif self.current_char == "=":
                tokens.append(self.make_equals())  # Handle = ==
            elif self.current_char == "<":
                tokens.append(self.make_less_than())  # Handle < <=
            elif self.current_char == ">":
                tokens.append(self.make_greater_than())  # Handle > >=
            elif self.current_char == ",":
                tokens.append(Token(TOKEN_TYPE_COMMA, pos_start=self.pos))
                self.advance()
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.advance()
                return [], IllegalCharError(
                    pos_start, self.pos, "'" + char + "'"
                )

        tokens.append(Token(TOKEN_TYPE_EOF, pos_start=self.pos))
        return tokens, None

    def make_exponent_number(self, num_str: str, pos_start: int) -> tuple:
        """
        An 'e' has been detected so at this point
        parse a floating point number which uses exponential notation
        e.g. 1.2e8 -2e4 -5e-5 +6e6 +1E6 1e-003
        """
        exponent_str = ""
        sign_str = ""
        if self.current_char in ["+", "-"]:
            sign_str = self.current_char
            self.advance()  # advance past the sign

        while self.current_char is not None and self.current_char in c.DIGITS:
            exponent_str += self.current_char
            self.advance()  # advance past the digit

        try:
            thenumber = float(num_str + "e" + sign_str + exponent_str)
            """
            Python uses JavaScript's Number.MAX_VALUE
            which is approximately 1.7976931348623157E+308
            Anything above that is given the value of Infinity i.e. 'inf'
            Check for this.
            Alternatively, Use 1e308 as the limit for a number too big!
            """
            if thenumber != 0 and (
                math.isinf(thenumber)
                or (thelog10 := math.log10(thenumber)) >= 308
            ):
                raise OverflowError
            elif thelog10 <= -308:
                return (
                    None,
                    InvalidSyntaxError(
                        pos_start, self.pos, c.ERRORS["exponent_underflow"]
                    ),
                )

            # Successful Parse
            return (
                Token(TOKEN_TYPE_FLOAT, thenumber, pos_start, self.pos),
                None,
            )

        except (OverflowError, MemoryError):
            return (
                None,
                InvalidSyntaxError(
                    pos_start, self.pos, c.ERRORS["exponent_overflow"]
                ),
            )

        except ValueError:
            # Number Conversion Error
            return (
                None,
                InvalidSyntaxError(
                    pos_start, self.pos, c.ERRORS["exponent_error"]
                ),
            )

    def make_number(self) -> tuple:
        """Parse a Number"""
        num_str = ""
        dot_count = 0
        pos_start = self.pos.copy()

        while (
            self.current_char is not None
            and self.current_char in c.NUMBER_CHARS
        ):

            if self.current_char == ".":
                if dot_count == 1:
                    # Numbers do not have two dots
                    break
                dot_count += 1

            elif self.current_char in ["e", "E"]:
                # Parse a floating-point number
                # which uses exponential notation
                self.advance()  # advance past the 'e'
                return self.make_exponent_number(num_str, pos_start)

            num_str += self.current_char
            self.advance()  # advance past the digit or '.'

        try:
            thenumber = int(num_str) if dot_count == 0 else float(num_str)
            # Check whether the converted number is too big
            if (
                thenumber != 0
                and (math.isinf(thenumber) or math.log10(thenumber)) >= 308
            ):
                raise OverflowError

            # Successful Convert to Number
            if dot_count == 0:
                # integer
                return (
                    Token(TOKEN_TYPE_INT, thenumber, pos_start, self.pos),
                    None,
                )
            else:
                # float/decimal number
                return (
                    Token(TOKEN_TYPE_FLOAT, thenumber, pos_start, self.pos),
                    None,
                )

        except (OverflowError, MemoryError):
            return (
                None,
                InvalidSyntaxError(
                    pos_start, self.pos, c.ERRORS["number_overflow"]
                ),
            )

        except ValueError:
            # Number Conversion Error
            return (
                None,
                InvalidSyntaxError(
                    pos_start, self.pos, c.ERRORS["number_conversion_error"]
                ),
            )

    def make_string(self) -> tuple:
        """Parse a String"""
        string = ""
        pos_start = self.pos.copy()
        escape_character_flag = False
        # Advance past the opening quote
        self.advance()

        while self.current_char is not None and (
            self.current_char != '"' or escape_character_flag
        ):

            if escape_character_flag and self.current_char == "x":
                escape_character_flag = False
                self.advance()
                result, error = self.handle_hex_value(pos_start)
                if error:
                    return None, error
                string += result
                continue

            if escape_character_flag:
                string += c.ESCAPE_CHARACTERS.get(
                    self.current_char, self.current_char
                )
                escape_character_flag = False
            else:
                if self.current_char == "\\":
                    escape_character_flag = True
                else:
                    string += self.current_char
            self.advance()

        if self.current_char is None:
            # Unterminated string
            return (
                None,
                InvalidSyntaxError(
                    pos_start, self.pos, c.ERRORS["unterminated_string"]
                ),
            )

        # Advance past the closing quote "
        self.advance()
        return Token(TOKEN_TYPE_STRING, string, pos_start, self.pos), None

    def handle_hex_value(self, pos_start: int) -> tuple:
        """
        Process escaped hex values
        Note: there must be TWO hexadecimal characters
        """
        # The hex value must be of the form \xhh
        char1, error = self.check_the_char(pos_start)
        if error:
            return char1, error
        # Advance past the first hex character
        self.advance()

        char2, error = self.check_the_char(pos_start)
        if error:
            return char2, error
        # Advance past the second hex character
        self.advance()

        return chr(int(char1, 16) * 16 + int(char2, 16)), None

    def check_the_char(self, pos_start: int) -> tuple:
        if self.current_char is None:
            # Unterminated string
            return (
                None,
                InvalidSyntaxError(
                    pos_start, self.pos, c.ERRORS["unterminated_string"]
                ),
            )

        if self.current_char not in c.HEX_CHARS:
            # Illegal hex character
            self.advance()
            return (
                None,
                InvalidSyntaxError(
                    pos_start, self.pos, c.ERRORS["illegal_hex_char"]
                ),
            )

        return self.current_char, None

    def make_identifier(self) -> Token:
        """Parse an Identifier"""
        id_str = ""
        pos_start = self.pos.copy()

        while (
            self.current_char is not None
            and self.current_char in c.LETTERS_DIGITS + "_"
        ):
            id_str += self.current_char
            self.advance()

        tok_type = (
            TOKEN_TYPE_KEYWORD if id_str in KEYWORDS else TOKEN_TYPE_IDENTIFIER
        )
        return Token(tok_type, id_str, pos_start, self.pos)

    def make_minus_or_arrow(self) -> Token:
        """Parse ->"""
        tok_type = TOKEN_TYPE_MINUS
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == ">":
            self.advance()
            tok_type = TOKEN_TYPE_ARROW

        return Token(tok_type, pos_start=pos_start, pos_end=self.pos)

    def make_not_equals(self) -> tuple:
        """Parse !="""
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            self.advance()
            # !=
            return (
                Token(
                    TOKEN_TYPE_NOT_EQUAL_TO,
                    pos_start=pos_start,
                    pos_end=self.pos,
                ),
                None,
            )

        self.advance()
        return None, ExpectedCharError(pos_start, self.pos, "'=' (after '!')")

    def make_equals(self) -> Token:
        """Parse = or =="""
        tok_type = TOKEN_TYPE_ASSIGN
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            # ==
            self.advance()
            tok_type = TOKEN_TYPE_EQUAL_TO

        # =
        return Token(tok_type, pos_start=pos_start, pos_end=self.pos)

    def make_less_than(self) -> Token:
        """Parse < or <="""
        tok_type = TOKEN_TYPE_LESS_THAN
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            # <=
            self.advance()
            tok_type = TOKEN_TYPE_LESS_THAN_EQUAL_TO

        # <
        return Token(tok_type, pos_start=pos_start, pos_end=self.pos)

    def make_greater_than(self) -> Token:
        """Parse > or >="""
        tok_type = TOKEN_TYPE_GREATER_THAN
        pos_start = self.pos.copy()
        self.advance()

        if self.current_char == "=":
            # >=
            self.advance()
            tok_type = TOKEN_TYPE_GREATER_THAN_EQUAL_TO

        # >
        return Token(tok_type, pos_start=pos_start, pos_end=self.pos)

    def skip_comment(self) -> tuple:
        """
        Single line comments begin with a #
        # ....

        Multiline Comments begin with #* and end with *#
        #* .... *#
        #* ....
        .... *#
        """

        multi_line_comment = False
        self.advance()
        if self.current_char == "*":
            multi_line_comment = True

        while True:
            if self.current_char == "*" and multi_line_comment:
                self.advance()
                if self.current_char != "#":
                    continue
                else:
                    break

            elif not multi_line_comment and (
                self.current_char == "\n" or self.current_char is None
            ):
                break

            elif self.current_char is None:
                # Unterminated Multiline Comment
                pos_start = self.pos.copy()
                # Generally the comment in question
                # would be on the previous line
                if pos_start.linenum:
                    pos_start.linenum -= 1

                return (
                    None,
                    InvalidSyntaxError(
                        pos_start,
                        self.pos,
                        c.ERRORS["unterminated_ML_comment"],
                    ),
                )

            self.advance()

        self.advance()
        # Success
        return None, None


#######################################
# NODES
#######################################


class NumberNode:
    def __init__(self, token: Token) -> None:
        self.token = token

        self.pos_start = self.token.pos_start
        self.pos_end = self.token.pos_end

    def __repr__(self) -> str:
        return f"{self.token}"


class StringNode:
    def __init__(self, token: Token) -> None:
        self.token = token

        self.pos_start = self.token.pos_start
        self.pos_end = self.token.pos_end

    def __repr__(self) -> str:
        return f"{self.token}"


class ListNode:
    """Generate 'element_nodes' which will be a list of Nodes"""

    def __init__(
        self, element_nodes: list, pos_start: int, pos_end: int
    ) -> None:
        self.element_nodes = element_nodes

        self.pos_start = pos_start
        self.pos_end = pos_end


class VarAccessNode:
    def __init__(self, var_name_token: Token) -> None:
        self.var_name_token = var_name_token

        self.pos_start = self.var_name_token.pos_start
        self.pos_end = self.var_name_token.pos_end


class VarAssignNode:
    def __init__(self, var_name_token: Token, value_node: Any) -> None:
        self.var_name_token = var_name_token
        self.value_node = value_node

        self.pos_start = self.var_name_token.pos_start
        # Record the end of the Assignment Expression
        self.pos_end = self.value_node.pos_end


class BinOpNode:
    def __init__(
        self, left_node: Any, operator_token: Token, right_node: Any
    ) -> None:
        self.left_node = left_node
        self.operator_token = operator_token
        self.right_node = right_node

        # Record the beginning of the Left Expression
        self.pos_start = self.left_node.pos_start
        # Record the end of the Right Expression
        self.pos_end = self.right_node.pos_end

    def __repr__(self) -> str:
        return f"({self.left_node}, {self.operator_token}, {self.right_node})"


class UnaryOpNode:
    def __init__(self, operator_token: Token, node: Any) -> None:
        self.operator_token = operator_token
        self.node = node

        self.pos_start = self.operator_token.pos_start
        # Record the end of the Unary Expression
        self.pos_end = node.pos_end

    def __repr__(self) -> str:
        return f"({self.operator_token}, {self.node})"


class IfNode:
    """Handle IF ... ELIF ... ELSE"""

    def __init__(self, cases: list, else_case: Any) -> None:
        self.cases = cases
        self.else_case = else_case

        # Record the beginning of the very first IF Conditional Expression
        self.pos_start = self.cases[0][0].pos_start

        # Either Record the end of an ELSE expression OR
        self.pos_end = (
            self.else_case
            or
            # Record the end of the very last IF Conditional Expression
            self.cases[len(self.cases) - 1]
        )[0].pos_end


class ForNode:
    def __init__(
        self,
        var_name_token: Token,
        start_value_node: Any,
        end_value_node: Any,
        step_value_node: Any,
        body_node: Any,
        should_return_none: bool,
    ) -> None:
        self.var_name_token = var_name_token
        self.start_value_node = start_value_node
        self.end_value_node = end_value_node
        self.step_value_node = step_value_node
        self.body_node = body_node
        self.should_return_none = should_return_none

        # Record the beginning of the FOR Expression
        self.pos_start = self.var_name_token.pos_start
        # Record the end of the body of the FOR Expression
        self.pos_end = self.body_node.pos_end


class WhileNode:
    def __init__(
        self, condition_node: Any, body_node: Any, should_return_none: bool
    ) -> None:
        self.condition_node = condition_node
        self.body_node = body_node
        self.should_return_none = should_return_none

        # Record the beginning of the WHILE Expression
        self.pos_start = self.condition_node.pos_start
        # Record the end of the body of the WHILE Expression
        self.pos_end = self.body_node.pos_end


class FuncDefNode:
    def __init__(
        self,
        var_name_token: Token,
        arg_name_tokens: list[Token],
        body_node: Any,
        should_auto_return: bool,
    ) -> None:
        self.var_name_token = var_name_token
        self.arg_name_tokens = arg_name_tokens
        self.body_node = body_node
        self.should_auto_return = should_auto_return

        if self.var_name_token:
            # This FUN has a name - record its position
            self.pos_start = self.var_name_token.pos_start
        elif len(self.arg_name_tokens) > 0:
            # Anonymous FUN - record the beginning of the FIRST Arg
            self.pos_start = self.arg_name_tokens[0].pos_start
        else:
            # Anonymous FUN, No Args! Body only!
            # Record the beginning of the body of the FUN expression
            self.pos_start = self.body_node.pos_start

        # Record the end of the body of the FUN expression
        self.pos_end = self.body_node.pos_end


class CallNode:
    # Handle the CALLing of a Function
    def __init__(self, node_to_call: Any, arg_nodes: list) -> None:
        self.node_to_call = node_to_call
        self.arg_nodes = arg_nodes

        # Record the beginning of the Function Call
        self.pos_start = self.node_to_call.pos_start

        if len(self.arg_nodes) > 0:
            # FUN with Args - Record the end of the LAST Arg
            self.pos_end = self.arg_nodes[len(self.arg_nodes) - 1].pos_end
        else:
            # FUN with No Args - Record the end of the Function Call
            self.pos_end = self.node_to_call.pos_end


class ReturnNode:
    def __init__(
        self, node_to_return: Any, pos_start: int, pos_end: int
    ) -> None:
        """
        This node represents the Return Value
        'node_to_return' will have the value of 'None'
        if a RETURN without an expression was parsed
        """
        self.node_to_return = node_to_return

        self.pos_start = pos_start
        self.pos_end = pos_end


class ContinueNode:
    def __init__(self, pos_start: int, pos_end: int) -> None:
        self.pos_start = pos_start
        self.pos_end = pos_end


class BreakNode:
    def __init__(self, pos_start: int, pos_end: int) -> None:
        self.pos_start = pos_start
        self.pos_end = pos_end


class ImportNode:
    def __init__(self, string_node: Any, pos_start: int, pos_end: int) -> None:
        self.string_node = string_node
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self) -> str:
        return f"IMPORT {self.string_node!r}"


#######################################
# PARSE RESULT
#######################################


class ParseResult:
    def __init__(self) -> None:
        self.error = None
        self.node = None
        self.last_registered_advance_count = 0
        self.advance_count = 0
        self.to_reverse_count = 0

    def register_advancement(self) -> None:
        # Advance By One Token
        self.last_registered_advance_count = 1
        self.advance_count += 1

    def register(self, result: Any) -> Any:
        """
        Make a note of the current number of tokens
        before an advancement is made
        ==> self.last_registered_advance_count

        Now advance by said amount 'result.advance_count'
        That is, add this value to 'self.advance_count'

        Register whether an error has occurred
        """
        self.last_registered_advance_count = result.advance_count
        self.advance_count += result.advance_count
        if result.error:
            self.error = result.error
        return result.node

    def try_register(self, result: Any) -> Any:
        if result.error:
            """
            An error has occurred therefore
            record the number of tokens needed to go
            back to the previous token position
            before the error occurred
            Hence, 'to_reverse_count'
            """
            self.to_reverse_count = result.advance_count
            return None

        # No error occurred - proceed forward
        return self.register(result)

    def success(self, node: Any) -> Self:
        # No errors
        self.node = node
        return self

    def failure(self, error: Any) -> Self:
        """
        An error has occurred
        If no error has been previously registered then
        Register the error now i.e.
        'self.error = error'
        """
        if not self.error or self.last_registered_advance_count == 0:
            self.error = error
        return self


#######################################
# PARSER
#######################################


class Parser:
    def __init__(self, tokens: list) -> None:
        self.tokens = tokens
        # After the first advancement the value will be 0
        self.token_index = -1
        # Process the initial token
        self.advance()

    def advance(self) -> Token:
        """Advance by One Token"""
        self.token_index += 1
        self.update_current_tok()
        # Return new token
        return self.current_token

    def reverse(self, amount: int = 1) -> Token:
        """
        An error has occurred therefore go
        back to the previous token position
        before the error occurred
        By subtracting 'amount' from the current 'token_index'
        """
        self.token_index -= amount
        # Reset to the 'token' at this new position
        self.update_current_tok()
        return self.current_token

    def update_current_tok(self) -> None:
        """Fetch Next Token"""
        if self.token_index >= 0 and self.token_index < len(self.tokens):
            self.current_token = self.tokens[self.token_index]

    def parse(self) -> Any:
        """
        Commence the Parsing of all the tokens produced by the Lexer
        Begin with
            in_a_function=False, in_a_loop=False
        """

        result = self.statements(False, False)
        if not result.error and self.current_token.type != TOKEN_TYPE_EOF:
            """
            This means there are still tokens 'left over'
            after Parsing as ended. Something therefore has gone wrong.
            Indicate this.
            """
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["tokens_out_of_place"],
                )
            )
        return result

    ###################################

    def statements(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """Parse a list of statements. Minimum: One Statement"""

        result = ParseResult()  # Initialise
        statements = []
        # Record the beginning of the First Statement
        pos_start = self.current_token.pos_start.copy()

        # To begin with, advance past any newlines \n or ;
        while self.current_token.type == TOKEN_TYPE_NEWLINE:
            result.register_advancement()  # Advance past the NL
            self.advance()

        # Parse a statement
        statement = result.register(self.statement(in_a_function, in_a_loop))
        if result.error:
            # Error occurred with the very first statement!
            return result

        # Successful parsed statement
        statements.append(statement)

        # Check for any further optional statements and parse them
        statements, result = self.parse_any_additional_statements(
            in_a_function, in_a_loop, statements, result
        )

        # Return a list of parsed statement nodes
        return result.success(
            # Record the end of the Last Statement
            ListNode(statements, pos_start, self.current_token.pos_end.copy())
        )

    def statement(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """Parse a single statement"""

        result = ParseResult()  # Initialise
        # Record the beginning of the Statement
        pos_start = self.current_token.pos_start.copy()

        if self.current_token.matches(TOKEN_TYPE_KEYWORD, "RETURN"):
            return self.parse_return(
                in_a_function, in_a_loop, result, pos_start
            )

        if self.current_token.matches(TOKEN_TYPE_KEYWORD, "CONTINUE"):
            return self.parse_continue(in_a_loop, result, pos_start)

        if self.current_token.matches(TOKEN_TYPE_KEYWORD, "BREAK"):
            return self.parse_break(in_a_loop, result, pos_start)

        if self.current_token.matches(TOKEN_TYPE_KEYWORD, "IMPORT"):
            return self.parse_import(
                in_a_function, in_a_loop, result, pos_start
            )

        # Otherwise Parse a single expression
        expression = result.register(self.expr(in_a_function, in_a_loop))
        if result.error:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["statement_syntax_error"],
                )
            )

        # Successful Parse
        return result.success(expression)

    def parse_any_additional_statements(
        self,
        in_a_function: bool,
        in_a_loop: bool,
        statements: list,
        result: ParseResult,
    ) -> ParseResult:
        """Check for any further optional statements and parse them"""

        more_statements = True

        while True:
            newline_count = 0
            while self.current_token.type == TOKEN_TYPE_NEWLINE:
                # To begin with, advance past any newlines \n or ;
                result.register_advancement()  # Advance past the NL
                self.advance()
                newline_count += 1  # Count each newline or ;

            if newline_count == 0:
                # Since the count is zero,
                # there are definitely no further statements
                more_statements = False

            # Are there any more statements?
            # If none, break the loop
            if not more_statements:
                break

            """
            Since a NL has been found,
            there is the possibility of another statement
            'try_register' will check to see if a valid statement follows
            """
            statement = result.try_register(
                self.statement(in_a_function, in_a_loop)
            )

            if not statement:
                """
                Since this is not a statement
                Revert back to the previous position
                Then indicate that there are no further statements
                """
                self.reverse(result.to_reverse_count)
                more_statements = False

                """
                Need to 'continue' this loop in order
                to advance past any further newlines
                as shown at the beginning of this While loop
                """

                continue

            # Successful parsed statement
            statements.append(statement)

        return statements, result

    def parse_return(
        self,
        in_a_function: bool,
        in_a_loop: bool,
        result: ParseResult,
        pos_start: int,
    ) -> ParseResult:
        """Parse the RETURN statement"""

        result.register_advancement()  # Advance past RETURN
        self.advance()

        # Check whether the RETURN is being used within a function
        if not in_a_function:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["bad_return"],
                )
            )

        """
        RETURN has the option of being followed by an EXPR
        So, does an EXPR follow?
        """
        expression = result.try_register(self.expr(in_a_function, in_a_loop))
        if not expression:
            # No! Revert to original position
            # This is a RETURN without an EXPR
            # therefore 'expr' has the value of None
            self.reverse(result.to_reverse_count)

        return result.success(
            ReturnNode(
                expression, pos_start, self.current_token.pos_start.copy()
            )
        )

    def parse_continue(
        self, in_a_loop: bool, result: ParseResult, pos_start: int
    ) -> ParseResult:
        """Parse the CONTINUE statement"""

        result.register_advancement()  # Advance past CONTINUE
        self.advance()
        # current_token.pos_start points to the token that follows CONTINUE

        # Check whether the CONTINUE is being used within a loop
        if not in_a_loop:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["bad_continue"],
                )
            )

        return result.success(
            ContinueNode(pos_start, self.current_token.pos_start.copy())
        )

    def parse_break(
        self, in_a_loop: bool, result: ParseResult, pos_start: int
    ) -> ParseResult:
        """Parse the BREAK statement"""

        result.register_advancement()  # Advance past BREAK
        self.advance()
        # current_token.pos_start points to the token that follows BREAK

        # Check whether the BREAK is being used within a loop
        if not in_a_loop:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["bad_break"],
                )
            )

        return result.success(
            BreakNode(pos_start, self.current_token.pos_start.copy())
        )

    def parse_import(
        self,
        in_a_function: bool,
        in_a_loop: bool,
        result: ParseResult,
        pos_start: int,
    ) -> ParseResult:
        """Parse the IMPORT <STRING> statement"""

        result.register_advancement()  # Advance past IMPORT
        self.advance()

        if not self.current_token.type == TOKEN_TYPE_STRING:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["string_expected"],
                )
            )

        string = result.register(self.atom(in_a_function, in_a_loop))
        # current_token.pos_start points to the token that follows
        # the IMPORT string
        return result.success(
            ImportNode(string, pos_start, self.current_token.pos_start.copy())
        )

    def expr(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """Parse a Single Expression"""

        result = ParseResult()  # Initialise

        if self.current_token.matches(TOKEN_TYPE_KEYWORD, "VAR"):
            # Parse VAR identifier = EXPR
            return self.parse_variable_assignment(
                in_a_function, in_a_loop, result
            )

        # Parse a non-assignment expression
        # This will always be a bin_op Binary Operation
        node = result.register(
            self.bin_op(
                in_a_function,
                in_a_loop,
                self.comp_expr,
                ((TOKEN_TYPE_KEYWORD, "AND"), (TOKEN_TYPE_KEYWORD, "OR")),
            )
        )

        if result.error:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["expr_syntax_error"],
                )
            )

        # Successful Parse
        return result.success(node)

    def parse_variable_assignment(
        self, in_a_function: bool, in_a_loop: bool, result: ParseResult
    ) -> ParseResult:
        """Parse VAR identifier = EXPR"""

        result.register_advancement()  # Advance past VAR
        self.advance()

        # Parse the Name of the Identifier
        if self.current_token.type != TOKEN_TYPE_IDENTIFIER:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["identifier_expected"],
                )
            )

        # Record the name
        var_name = self.current_token
        result.register_advancement()  # Advance past the Identifier
        self.advance()

        # Parse =
        if self.current_token.type != TOKEN_TYPE_ASSIGN:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["equal_expected"],
                )
            )

        result.register_advancement()  # Advance past =
        self.advance()

        # Parse the Assigned Expression
        expression = result.register(self.expr(in_a_function, in_a_loop))
        if result.error:
            return result

        # Successful Parse
        return result.success(VarAssignNode(var_name, expression))

    def comp_expr(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """Parse a Comparison Expression"""

        result = ParseResult()  # Initialise

        if self.current_token.matches(TOKEN_TYPE_KEYWORD, "NOT"):
            # Parse NOT EXPR
            operator_token = self.current_token
            result.register_advancement()  # Advance past NOT
            self.advance()

            # Handles NOT NOT ...
            node = result.register(self.comp_expr(in_a_function, in_a_loop))
            if result.error:
                return result

            # Successful Parse
            return result.success(UnaryOpNode(operator_token, node))

        node = result.register(
            self.bin_op(
                in_a_function,
                in_a_loop,
                self.arith_expr,
                COMPARISONS_TOKEN,
            )
        )

        if result.error:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["comp_syntax_error"],
                )
            )

        # Successful Parse
        return result.success(node)

    def arith_expr(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """Parse X + Y or X - Y"""
        return self.bin_op(
            in_a_function,
            in_a_loop,
            self.term,
            (TOKEN_TYPE_PLUS, TOKEN_TYPE_MINUS),
        )

    def term(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """Parse X * Y or X / Y or X % Y"""
        return self.bin_op(
            in_a_function,
            in_a_loop,
            self.factor,
            (TOKEN_TYPE_MULTIPLY, TOKEN_TYPE_DIVIDE, TOKEN_TYPE_MODULUS),
        )

    def factor(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """Parse +X or -X"""
        result = ParseResult()  # Initialise
        token = self.current_token

        if token.type in (TOKEN_TYPE_PLUS, TOKEN_TYPE_MINUS):
            result.register_advancement()  # Advance past + OR -
            self.advance()
            factor = result.register(self.factor(in_a_function, in_a_loop))
            if result.error:
                return result

            # Handles - - ... OR even + + ...
            return result.success(UnaryOpNode(token, factor))

        return self.power(in_a_function, in_a_loop)

    def power(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """Parse x^y"""
        return self.bin_op(
            in_a_function,
            in_a_loop,
            self.call,
            (TOKEN_TYPE_POWER,),
            self.factor,
        )

    def call(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """
        Parse function_call(x,...) OR function_call() OR ATOM"""
        result = ParseResult()  # Initialise

        # This in turn, enables higher-order functions
        atom = result.register(self.atom(in_a_function, in_a_loop))
        if result.error:
            return result

        if self.current_token.type != TOKEN_TYPE_LPAREN:
            """
            This is NOT a Function Call
            An 'atom' can be either a number, a string,
            a variable, a parenthesised expression (expr), a list,
            IF expression, FOR expression, WHILE expression or
            a FUN definition
            atom() will be called at this point to parse it
            """
            return result.success(atom)

        """
        Otherwise parse a Function Call
        which would bb either of these two forms:
        function()
        function(arg1, ...)
        """

        result.register_advancement()  # Advance past the Left Parenthesis
        self.advance()
        # List of argument nodes which can be empty i.e. []
        arg_nodes = []

        if self.current_token.type == TOKEN_TYPE_RPAREN:
            # Advance past the Right Parenthesis
            # This is a Function Call without arguments i.e. func()
            result.register_advancement()
            self.advance()
        else:
            # Parse the first argument
            the_arg = self.expr(in_a_function, in_a_loop)
            arg_nodes.append(result.register(the_arg))
            if result.error:
                return result.failure(
                    InvalidSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        c.ERRORS["arg1_syntax_error"],
                    )
                )

            # Optionally more arguments could follow preceded by a comma
            while self.current_token.type == TOKEN_TYPE_COMMA:
                result.register_advancement()  # Advance past ,
                self.advance()

                # Parse an argument
                the_arg = self.expr(in_a_function, in_a_loop)
                arg_nodes.append(result.register(the_arg))
                if result.error:
                    return result

            # if no comma, then the closing right parenthesis must follow
            if self.current_token.type != TOKEN_TYPE_RPAREN:
                return result.failure(
                    InvalidSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        c.ERRORS["comma_rparen_expected"],
                    )
                )

            # Advance past the Right Parenthesis
            result.register_advancement()
            self.advance()
        return result.success(CallNode(atom, arg_nodes))

    def atom(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """
        Parse a number or a string or a Variable or
        (EXPR) or [...] or IF or FOR or WHILE or FUN
        """
        result = ParseResult()  # Initialise
        token = self.current_token

        if token.type in (TOKEN_TYPE_INT, TOKEN_TYPE_FLOAT):
            # Parse a Number
            result.register_advancement()  # Advance past the Number
            self.advance()
            # Successful Parse
            return result.success(NumberNode(token))

        elif token.type == TOKEN_TYPE_STRING:
            # Parse a String
            result.register_advancement()  # Advance past the String
            self.advance()
            # Successful Parse
            return result.success(StringNode(token))

        elif token.type == TOKEN_TYPE_IDENTIFIER:
            # Parse an Identifier
            result.register_advancement()  # Advance past the Identifier
            self.advance()
            # Successful Parse
            return result.success(VarAccessNode(token))

        elif token.type == TOKEN_TYPE_LPAREN:
            # Parse (EXPR)
            result.register_advancement()  # Advance past the Left Parenthesis
            self.advance()
            # Parse EXPR
            expr = result.register(self.expr(in_a_function, in_a_loop))
            if result.error:
                return result
            # Closing Parenthesis
            if self.current_token.type == TOKEN_TYPE_RPAREN:
                # Advance past the Right Parenthesis
                result.register_advancement()
                self.advance()
                # Successful Parse
                return result.success(expr)
            else:
                return result.failure(
                    InvalidSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        c.ERRORS["rparen_expected"],
                    )
                )

        elif token.type == TOKEN_TYPE_LSQUARE:
            # Parse [EXPR, ...], []
            list_expr = result.register(
                self.list_expr(in_a_function, in_a_loop)
            )
            if result.error:
                return result
            # Successful Parse
            return result.success(list_expr)

        elif token.matches(TOKEN_TYPE_KEYWORD, "IF"):
            # Parse IF expression
            if_expr = result.register(self.if_expr(in_a_function, in_a_loop))
            if result.error:
                return result
            # Successful Parse
            return result.success(if_expr)

        elif token.matches(TOKEN_TYPE_KEYWORD, "FOR"):
            # Parse FOR expression
            # True indicates that a Loop is being parsed
            for_expr = result.register(self.for_expr(in_a_function, True))
            if result.error:
                return result
            # Successful Parse
            return result.success(for_expr)

        elif token.matches(TOKEN_TYPE_KEYWORD, "WHILE"):
            # Parse WHILE expression
            # True indicates that a Loop is being parsed
            while_expr = result.register(self.while_expr(in_a_function, True))
            if result.error:
                return result
            # Successful Parse
            return result.success(while_expr)

        elif token.matches(TOKEN_TYPE_KEYWORD, "FUN"):
            # Parse FUN expression
            # True indicates that a Function Definition is being parsed
            func_def = result.register(self.func_def(True, in_a_loop))
            if result.error:
                return result
            # Successful Parse
            return result.success(func_def)

        return result.failure(
            InvalidSyntaxError(
                token.pos_start,
                token.pos_end,
                c.ERRORS["atom_syntax_error"],
            )
        )

    def list_expr(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """
        Parse a List of Expressions [EXPR, ...] which an be empty i.e. []
        Need to also handle nested lists
        """
        result = ParseResult()  # Initialise
        element_nodes = []
        # Record the beginning of the List
        pos_start = self.current_token.pos_start.copy()

        # This has to be a Left Bracket
        if self.current_token.type != TOKEN_TYPE_LSQUARE:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["lbracket_expected"],
                )
            )

        result.register_advancement()  # Advance past the Left Bracket
        self.advance()

        if self.current_token.type == TOKEN_TYPE_RSQUARE:
            # This is an empty list []
            result.register_advancement()  # Advance past the Right Bracket
            self.advance()
            # Parsed an empty list i.e. []
            return result.success(
                ListNode(
                    element_nodes, pos_start, self.current_token.pos_end.copy()
                )
            )

        # Parse a nonempty list [elem1, ...]
        # Parse the first EXPR
        expression = result.register(self.expr(in_a_function, in_a_loop))
        element_nodes.append(expression)
        if result.error:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["list_element_expected"],
                )
            )

        # Optionally more EXPRs could follow preceded by a comma
        while self.current_token.type == TOKEN_TYPE_COMMA:
            result.register_advancement()  # Advance past ,
            self.advance()

            # Parse an Expression
            expression = result.register(self.expr(in_a_function, in_a_loop))
            element_nodes.append(expression)
            if result.error:
                return result

        # Parse Closing Bracket
        if self.current_token.type != TOKEN_TYPE_RSQUARE:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["comma_rbracket_expected"],
                )
            )

        # Advance past the Closing Right Bracket
        result.register_advancement()
        self.advance()

        # Successful Parse
        return result.success(
            ListNode(
                element_nodes, pos_start, self.current_token.pos_end.copy()
            )
        )

    def if_expr(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """
        Parse IF Expression/Statement

        IF Expression:
            IF condition THEN expr
            IF condition THEN expr1 ELSE expr2
            IF cond1 THEN expr1 ELIF cond2 THEN expr3 ... ELIF ... END
            IF c1 THEN expr1 ELIF c2 THEN expr3 ... ELIF ... ELSE exprn END

        IF Multiline Statement:
            IF condition THEN
                ...
                ...
                ...
            END

            IF condition THEN
                ...
                ...
                ...
            ELSE
                ...
                ...
                ...
            END

            IF condition THEN
                ...
                ...
            ELIF condition THEN
                ...
                ...
            ELIF condition THEN
                ...
                ...
            END

            IF condition THEN
                ...
                ...
            ELIF condition THEN
                ...
                ...
            ELSE
                ...
                ...
            END

        Grammar:
        if-expr     : KEYWORD:IF expr KEYWORD:THEN
                     (statement if-expr-b|if-expr-c?)
                    | (NEWLINE statements KEYWORD:END|if-expr-b|if-expr-c)
        """

        result = ParseResult()  # Initialise
        # Parse the entire IF expression/statement
        all_cases = result.register(
            self.if_expr_cases("IF", in_a_function, in_a_loop)
        )
        if result.error:
            return result

        """
        Split the result into a tuple
        The first element contains all the IF/ELIF nodes
        The second element contains the ELSE node
        which could have the value 'None' if there is no ELSE expr
        """
        cases, else_case = all_cases
        return result.success(IfNode(cases, else_case))

    def if_expr_b(self, in_a_function: bool, in_a_loop: bool) -> Any:
        """
        Parse all the ELIF expressions/statements

        Grammar:
        if-expr-b   : KEYWORD:ELIF expr KEYWORD:THEN
                      (statement if-expr-b|if-expr-c?)
                    | (NEWLINE statements KEYWORD:END|if-expr-b|if-expr-c)
        """
        return self.if_expr_cases("ELIF", in_a_function, in_a_loop)

    def if_expr_c(self, in_a_function: bool, in_a_loop: bool) -> Any:
        """
        Parse the ELSE expression/statement

        Grammar:
        if-expr-c   : KEYWORD:ELSE
                      statement
                    | (NEWLINE statements KEYWORD:END)
        """
        result = ParseResult()  # Initialise
        else_case = None

        if self.current_token.matches(TOKEN_TYPE_KEYWORD, "ELSE"):
            result.register_advancement()  # Advance past ELSE
            self.advance()

            if self.current_token.type == TOKEN_TYPE_NEWLINE:
                # ELSE followed by a NL indicates a Multiline ELSE
                else_case, error = self.parse_multiline_else(
                    in_a_function, in_a_loop, result
                )
                if error:
                    return error
                else:
                    # Successful ELSE parse
                    return result.success(else_case)

            # This is an ELSE expression - Parse it
            expr = result.register(self.statement(in_a_function, in_a_loop))
            if result.error:
                return result

            """
            Successful parse
            'False' indicates that 'should_return_none' is set to False
            Because an ELSE expression does return a value
            """
            else_case = (expr, False)

        # This will have the value None
        # if there is no ELSE statement/expression
        return result.success(else_case)

    def if_expr_b_or_c(
        self, in_a_function: bool, in_a_loop: bool
    ) -> ParseResult:
        """Parse ELIF/ELSE Expressions/Statements"""
        result = ParseResult()  # Initialise
        cases, else_case = [], None

        if self.current_token.matches(TOKEN_TYPE_KEYWORD, "ELIF"):
            # Handle ELIF
            all_cases = result.register(
                self.if_expr_b(in_a_function, in_a_loop)
            )
            if result.error:
                return result
            cases, else_case = all_cases
        else:
            # Handle ELSE
            else_case = result.register(
                self.if_expr_c(in_a_function, in_a_loop)
            )
            if result.error:
                return result

        return result.success((cases, else_case))

    def if_expr_cases(
        self, case_keyword: str, in_a_function: bool, in_a_loop: bool
    ) -> ParseResult:
        """Parse IF/ELIF Expressions/Statements"""
        result = ParseResult()  # Initialise
        cases = []
        else_case = None

        if not self.current_token.matches(TOKEN_TYPE_KEYWORD, case_keyword):
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    f"Expected '{case_keyword}'",
                )
            )

        # Advance past the Keyword in case_keyword
        # i.e. advance past either 'IF' or 'ELIF'
        result.register_advancement()
        self.advance()

        # Parse the IF condition
        condition = result.register(self.expr(in_a_function, in_a_loop))
        if result.error:
            return result

        if not self.current_token.matches(TOKEN_TYPE_KEYWORD, "THEN"):
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["then_expected"],
                )
            )

        result.register_advancement()  # Advance past THEN
        self.advance()

        # Multiline statements begin with a newline \n or ;
        if self.current_token.type == TOKEN_TYPE_NEWLINE:
            # THEN followed by a NL indicates Multiline IF/ELIF
            cases, else_case, error = self.parse_multiline_then(
                in_a_function, in_a_loop, condition, result
            )
            if error:
                return error
            else:
                # Successful THEN parse
                return result.success((cases, else_case))

        # This is a single IF expression - Parse it
        expr = result.register(self.statement(in_a_function, in_a_loop))
        if result.error:
            return result

        """
        'False' indicates that 'should_return_none' is set to False
        Because an IF expression does return a value
        """
        cases.append((condition, expr, False))

        all_cases = result.register(
            self.if_expr_b_or_c(in_a_function, in_a_loop)
        )
        if result.error:
            return result

        new_cases, else_case = all_cases
        cases.extend(new_cases)

        # Successful Parse
        return result.success((cases, else_case))

    def parse_multiline_else(
        self, in_a_function: bool, in_a_loop: bool, result: ParseResult
    ) -> Any:
        """Parse ELSE Multiline statements"""

        result.register_advancement()  # Advance past the NL
        self.advance()

        # Parse the statements
        statements = result.register(self.statements(in_a_function, in_a_loop))
        if result.error:
            return result

        """
        'True' indicates that 'should_return_none' is set to True
        Because ELSE statement(s) do not return a value
        """
        else_case = (statements, True)

        if self.current_token.matches(TOKEN_TYPE_KEYWORD, "END"):
            result.register_advancement()  # Advance past END
            self.advance()
        else:
            return (
                None,
                result.failure(
                    InvalidSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        c.ERRORS["end_expected"],
                    )
                ),
            )

        # Successful Parse
        return else_case, None

    def parse_multiline_then(
        self,
        in_a_function: bool,
        in_a_loop: bool,
        condition: ParseResult,
        result: ParseResult,
    ) -> tuple[None, None, Any] | tuple[list, Any | None, None]:
        """Parse THEN Multiline statements"""

        cases = []
        else_case = None
        result.register_advancement()  # Advance past the NL
        self.advance()

        # Parse the statements
        statements = result.register(self.statements(in_a_function, in_a_loop))
        if result.error:
            return None, None, result

        """
        'True' indicates that 'should_return_none' is set to True
        Because IF statement(s) do not return a value
        """
        cases.append((condition, statements, True))

        if self.current_token.matches(TOKEN_TYPE_KEYWORD, "END"):
            result.register_advancement()  # Advance past END
            self.advance()
        else:
            # Handle ELIF and ELSE statements
            all_cases = result.register(
                self.if_expr_b_or_c(in_a_function, in_a_loop)
            )
            if result.error:
                return None, None, result

            new_cases, else_case = all_cases
            cases.extend(new_cases)

        # Successful Parse
        return cases, else_case, None

    def for_expr(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """
        Parse FOR Expression/Statement

        FOR Expression:
            FOR identifier = expr1 TO expr2 THEN expr3
            FOR identifier = expr1 TO expr2 STEP expr3 THEN expr4

        FOR Multiline Statement:
            FOR identifier = expr1 TO expr2 THEN
                ...
                ...
            END

            FOR identifier = expr1 TO expr2 STEP expr3 THEN
                ...
                ...
            END

        Grammar:
        for-expr    : KEYWORD:FOR IDENTIFIER EQ expr KEYWORD:TO expr
                      (KEYWORD:STEP expr)? KEYWORD:THEN
                      statement
                    | (NEWLINE statements KEYWORD:END)

        """
        result = ParseResult()  # Initialise

        if not self.current_token.matches(TOKEN_TYPE_KEYWORD, "FOR"):
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["for_expected"],
                )
            )

        result.register_advancement()  # Advance past FOR
        self.advance()

        if self.current_token.type != TOKEN_TYPE_IDENTIFIER:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["identifier_expected"],
                )
            )

        var_name = self.current_token
        result.register_advancement()  # Advance past the Identifier
        self.advance()

        if self.current_token.type != TOKEN_TYPE_ASSIGN:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["equal_expected"],
                )
            )

        result.register_advancement()  # Advance past =
        self.advance()

        # Parse the FOR's Start expression
        start_value = result.register(self.expr(in_a_function, in_a_loop))
        if result.error:
            return result

        if not self.current_token.matches(TOKEN_TYPE_KEYWORD, "TO"):
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["to_expected"],
                )
            )

        result.register_advancement()  # Advance past TO
        self.advance()

        # Parse the FOR's TO/End expression
        end_value = result.register(self.expr(in_a_function, in_a_loop))
        if result.error:
            return result

        if self.current_token.matches(TOKEN_TYPE_KEYWORD, "STEP"):
            result.register_advancement()  # Advance past STEP
            self.advance()

            # Parse the FOR's STEP expression
            step_value = result.register(self.expr(in_a_function, in_a_loop))
            if result.error:
                return result
        else:
            # This indicates that there is no STEP expression
            step_value = None

        if not self.current_token.matches(TOKEN_TYPE_KEYWORD, "THEN"):
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["then_expected"],
                )
            )

        result.register_advancement()  # Advance past THEN
        self.advance()

        if self.current_token.type != TOKEN_TYPE_NEWLINE:
            # This is a single FOR expression - Parse it
            body = result.register(self.statement(in_a_function, in_a_loop))
            if result.error:
                return result

            """
            Successful Parse
            'False' indicates that 'should_return_none' is set to False
            Because a FOR expression does return a value
            """
            return result.success(
                ForNode(
                    var_name, start_value, end_value, step_value, body, False
                )
            )

        # Otherwise
        # Multiline statements begin with a newline \n or ;
        result.register_advancement()  # Advance past the NL
        self.advance()

        # Parse the FOR's Multiline statements
        body = result.register(self.statements(in_a_function, in_a_loop))
        if result.error:
            return result

        if not self.current_token.matches(TOKEN_TYPE_KEYWORD, "END"):
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["end_expected"],
                )
            )

        result.register_advancement()  # Advance past END
        self.advance()

        """
        Successful Parse
        'True' indicates that 'should_return_none' is set to True
        Because FOR statement(s) do not return a value
        """
        return result.success(
            ForNode(var_name, start_value, end_value, step_value, body, True)
        )

    def while_expr(self, in_a_function: bool, in_a_loop: bool) -> ParseResult:
        """
        Parse WHILE Expression/Statement

        WHILE Expression:
            WHILE expr1 THEN expr2

        WHILE Multiline Statement:
            WHILE expr THEN
                ...
                ...
            END
        """
        result = ParseResult()  # Initialise

        if not self.current_token.matches(TOKEN_TYPE_KEYWORD, "WHILE"):
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["while_expected"],
                )
            )

        result.register_advancement()  # Advance past WHILE
        self.advance()

        # Parse the WHILE condition
        condition = result.register(self.expr(in_a_function, in_a_loop))
        if result.error:
            return result

        if not self.current_token.matches(TOKEN_TYPE_KEYWORD, "THEN"):
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["then_expected"],
                )
            )

        result.register_advancement()  # Advance past THEN
        self.advance()

        if self.current_token.type != TOKEN_TYPE_NEWLINE:
            # This is a single WHILE expression - Parse it
            body = result.register(self.statement(in_a_function, in_a_loop))
            if result.error:
                return result

            """
            Successful Parse
            'False' indicates that 'should_return_none' is set to False
            Because a WHILE expression does return a value
            """
            return result.success(WhileNode(condition, body, False))

        # Otherwise
        # Multiline statements begin with a newline \n or ;
        result.register_advancement()  # Advance past the NL
        self.advance()

        # Parse the WHILE's Multiline statements
        body = result.register(self.statements(in_a_function, in_a_loop))
        if result.error:
            return result

        if not self.current_token.matches(TOKEN_TYPE_KEYWORD, "END"):
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["end_expected"],
                )
            )

        result.register_advancement()  # Advance past END
        self.advance()

        """
        Successful Parse
        'True' indicates that 'should_return_none' is set to True
        Because WHILE statement(s) do not return a value
        """
        return result.success(WhileNode(condition, body, True))

    def func_def(self, in_a_function: bool, in_a_loop: bool) -> Any:
        """
        Parse FUN Expression/Statement

        FUN Expression:
            FUN function_name (parameter(s)) -> expr
            e.g. FUN afunc(a,b) -> a + b

            FUN (parameter(s)) -> expr
            Anonymous Function
            e.g. FUN (a,b) -> a + b

            FUN function_name () -> expr
            e.g. FUN pi() -> 3.141592558

            FUN () -> expr
            Anonymous Function
            e.g. FUN () -> 3.141592558
        """
        result = ParseResult()  # Initialise

        if not self.current_token.matches(TOKEN_TYPE_KEYWORD, "FUN"):
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["fun_expected"],
                )
            )

        result.register_advancement()  # Advance past FUN
        self.advance()

        if self.current_token.type == TOKEN_TYPE_IDENTIFIER:
            # Parse FUN function_name followed by LPAREN
            var_name_token = self.current_token
            result.register_advancement()  # Advance past the Identifier
            self.advance()
            # Left Parenthesis must follow
            if self.current_token.type != TOKEN_TYPE_LPAREN:
                return result.failure(
                    InvalidSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        c.ERRORS["lparen_expected"],
                    )
                )
        else:
            # Parse anonymous function: FUN followed by LPAREN
            var_name_token = None
            # Left Parenthesis must follow
            if self.current_token.type != TOKEN_TYPE_LPAREN:
                return result.failure(
                    InvalidSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        c.ERRORS["identifier_lparen_expected"],
                    )
                )

        result.register_advancement()  # Advance past the Opening Parenthesis
        self.advance()
        param_name_tokens = []

        # Either an identifier or a RPAREN must follow
        if self.current_token.type == TOKEN_TYPE_IDENTIFIER:
            pass
        elif self.current_token.type != TOKEN_TYPE_RPAREN:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["identifier_rparen_expected"],
                )
            )

        """
        Parse the function's parameters if any
        Upon completion, if it turns out to be an arrow function,
        then complete the parsing of
        the entire arrow function definition
        """
        tuple = self.parse_params_and_arrow(
            result, var_name_token, param_name_tokens
        )

        (parsed_arrow, result, param_name_tokens, error) = tuple

        if error:
            # An error occurred
            return error

        if parsed_arrow:
            # An arrow function has been parsed successfully
            return parsed_arrow

        # At this stage, it must be a Multiline FUN definition
        # Therefore, a NEWLINE token must follow
        if self.current_token.type != TOKEN_TYPE_NEWLINE:
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["arrow_NL_expected"],
                )
            )

        result.register_advancement()  # Advance past the NL
        self.advance()

        """
        Parse the FUN's multiline definition's body
        Since this is the body of a new function definition
        Commence the Parsing with
        in_a_function=True, in_a_loop=False
        """
        in_a_function = True
        in_a_loop = False
        body = result.register(self.statements(in_a_function, in_a_loop))
        if result.error:
            return result

        if not self.current_token.matches(TOKEN_TYPE_KEYWORD, "END"):
            return result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["end_expected"],
                )
            )

        result.register_advancement()  # Advance past END
        self.advance()

        """
        Successful Parse
        'False' indicates that 'should_auto_return' is set to False
        This means that this is a non-arrow function.
        It acts more like a procedure.
        Therefore, there may be no return value at all!
        That is,
        1) If this function executes a RETURN expr
        the value of this expresson would be returned
        2) If this function executes a RETURN without an expr
        a None value of 0 will be returned viz. 'Number.none'
        3) If the function executes no RETURN at all,
        a None value of 0 will be returned when the function as ended
        viz. 'Number.none'
        """

        return result.success(
            FuncDefNode(
                var_name_token, param_name_tokens, body, False
            )  # should_auto_return
        )

    def parse_params_and_arrow(
        self,
        result: ParseResult,
        var_name_token: Token,
        param_name_tokens: list[Token],
    ) -> tuple:
        """
        Parse the function's parameters if any
        Upon completion, if it turns out to be an arrow function,
        e.g. (parameter(s)) -> expr OR () -> expr
        then complete the parsing of
        the entire arrow function definition

        At this stage, pointing at the first parameter or at a RPAREN
        """

        if self.current_token.type == TOKEN_TYPE_RPAREN:
            return self.checkfor_parse_arrow(
                result, var_name_token, param_name_tokens
            )

        # This list will have the actual parameter names so that
        # a check can be verified that there are no duplicates
        names_list = []
        # This is the current function name so that
        # a check can be verified that there are no duplicates
        function_name = var_name_token.value

        # Parse the first parameter
        param_name_tokens.append(self.current_token)
        names_list.append(self.current_token.value)

        """
        Check whether the function name
        has been used as a parameter name as well
        """
        if error := self.duplicate_function_name(
            function_name, names_list, result
        ):
            return error

        result.register_advancement()  # Advance past the Identifier
        self.advance()

        # Optionally more parameters could follow preceded by a comma
        while self.current_token.type == TOKEN_TYPE_COMMA:
            result.register_advancement()  # Advance past ,
            self.advance()

            if self.current_token.type != TOKEN_TYPE_IDENTIFIER:
                error = result.failure(
                    InvalidSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        c.ERRORS["identifier_expected"],
                    )
                )
                return None, None, [], error

            # Parse a parameter - Check for duplicates
            if self.current_token.value in names_list:
                error = result.failure(
                    InvalidSyntaxError(
                        self.current_token.pos_start,
                        self.current_token.pos_end,
                        (
                            "Duplicate parameter "
                            f"'{self.current_token.value}' "
                            "in function definition"
                        ),
                    )
                )
                return None, None, [], error

            param_name_tokens.append(self.current_token)
            names_list.append(self.current_token.value)
            # Check if the function name has already been used
            if error := self.duplicate_function_name(
                function_name, names_list, result
            ):
                return error

            result.register_advancement()  # Advance past the Identifier
            self.advance()

        if self.current_token.type != TOKEN_TYPE_RPAREN:
            error = result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    c.ERRORS["comma_rparen_expected"],
                )
            )
            return None, None, [], error

        return self.checkfor_parse_arrow(
            result, var_name_token, param_name_tokens
        )

    def checkfor_parse_arrow(
        self,
        result: ParseResult,
        var_name_token: Token,
        param_name_tokens: list[Token],
    ) -> tuple:
        """
        Check to see if this is an arrow function
        If so, complete the parsing of
        the entire arrow function definition

        At this stage, pointing at the right parenthesis
        """

        # Advance past the Closing Right Parenthesis
        result.register_advancement()
        self.advance()

        if self.current_token.type != TOKEN_TYPE_ARROW:
            # Not an Arrow Function therefore must be
            # a Multiline definition
            # The first 'None' indicates that this is NOT an arrow function!
            return None, result, param_name_tokens, None

        result.register_advancement()  # Advance past ->
        self.advance()

        """
        Parse the arrow function definition's body
        Since this is the body of a new function definition
        Commence the Parsing with
        in_a_function=True, in_a_loop=False
        """
        body = result.register(self.expr(True, False))
        if result.error:
            return None, None, [], result

        """
        Successful Parse
        'True' indicates that 'should_auto_return' is set to True
        This means that this is an 'Arrow' function defined with ->
        Such functions AUTOmatically return a value after execution
        """

        parsed_arrow = result.success(
            FuncDefNode(
                var_name_token, param_name_tokens, body, True
            )  # should_auto_return
        )

        # This IS an arrow function!
        return parsed_arrow, result, param_name_tokens, None

    def duplicate_function_name(
        self, function_name: str, names_list: list, result: ParseResult
    ) -> Any:
        """
        Check whether the function name
        has been used as a parameter name as well
        """

        # Parse a parameter - Check for duplicates
        if function_name in names_list:
            error = result.failure(
                InvalidSyntaxError(
                    self.current_token.pos_start,
                    self.current_token.pos_end,
                    (
                        f"Duplicate parameter '{function_name}'. "
                        "A parameter cannot share the same name "
                        "as the function name"
                    ),
                )
            )
            return None, None, [], error

    ###################################

    def bin_op(
        self,
        in_a_function: bool,
        in_a_loop: bool,
        func_a: Any,
        ops: list,
        func_b: Any = None,
    ) -> ParseResult:
        if func_b is None:
            func_b = func_a

        result = ParseResult()  # Initialise
        left = result.register(func_a(in_a_function, in_a_loop))
        if result.error:
            return result

        while (
            self.current_token.type in ops
            or (self.current_token.type, self.current_token.value) in ops
        ):
            operator_token = self.current_token
            result.register_advancement()  # Advance past the Operator Token
            self.advance()
            right = result.register(func_b(in_a_function, in_a_loop))
            if result.error:
                return result
            left = BinOpNode(left, operator_token, right)

        return result.success(left)


#######################################
# RUNTIME RESULT
#######################################


class RTResult:
    def __init__(self) -> None:
        self.reset()

    def reset(self):
        self.value = None
        self.error = None
        self.func_return_value = None
        self.loop_should_continue = False
        self.loop_should_break = False

    def register(self, result: ParseResult | Exception) -> Any:
        self.error = result.error
        self.func_return_value = result.func_return_value
        self.loop_should_continue = result.loop_should_continue
        self.loop_should_break = result.loop_should_break
        return result.value

    def success(self, value: Any) -> Self:
        self.reset()
        self.value = value
        return self

    def success_return(self, value: Any) -> Self:
        self.reset()
        self.func_return_value = value
        return self

    def success_continue(self) -> Self:
        self.reset()
        self.loop_should_continue = True
        return self

    def success_break(self) -> Self:
        self.reset()
        self.loop_should_break = True
        return self

    def failure(self, error) -> Self:
        self.reset()
        self.error = error
        return self

    def should_return(self) -> Any:
        # Note: this will enable to 'continue' a loop and
        # 'break' a loop as well as
        # 'break' outside the current function
        return (
            self.error  # an error has occurred
            or self.func_return_value  # executing a RETURN from a function
            or self.loop_should_continue  # executing a CONTINUE the loop
            or self.loop_should_break  # executing a BREAK from loop
        )


#######################################
# VALUES
#######################################


class Value:
    def __init__(self) -> None:
        self.set_pos()
        self.set_context()

    def set_pos(
        self, pos_start: Optional[int] = None, pos_end: Optional[int] = None
    ) -> Self:
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def set_context(self, context: Optional[Any] = None) -> Self:
        self.context = context
        return self

    def added_to(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def subtracted_by(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def multiplied_by(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def divided_by(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def modulused_by(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def powered_by(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def get_comparison_eq(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def get_comparison_ne(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def get_comparison_lt(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def get_comparison_gt(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def get_comparison_lte(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def get_comparison_gte(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def anded_by(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def ored_by(self, other: Any) -> tuple:
        return None, self.illegal_operation(other)

    def notted(self, other: Optional[Any] = None) -> tuple:
        return None, self.illegal_operation(other)

    def execute(self, args: list) -> RTResult:
        return RTResult().failure(self.illegal_operation())

    def copy(self) -> Exception:
        raise Exception("No copy method defined")

    def is_true(self) -> bool:
        return False

    def illegal_operation(self, other: Optional[Any] = None) -> RTError:
        if not other:
            other = self
        return RTError(
            self.pos_start, other.pos_end, "Illegal operation", self.context
        )


class Number(Value):
    def __init__(self, value: Any) -> None:
        super().__init__()
        self.value = value

    def added_to(self, other: Any) -> tuple:
        """Addition: number1 + number2"""
        if isinstance(other, Number):
            return (
                Number(self.value + other.value).set_context(self.context),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def subtracted_by(self, other: Any) -> tuple:
        """Subtraction: number1 - number2"""
        if isinstance(other, Number):
            return (
                Number(self.value - other.value).set_context(self.context),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def multiplied_by(self, other: Any) -> tuple:
        """Multiplication: number1 * number2"""
        if isinstance(other, Number):
            return (
                Number(self.value * other.value).set_context(self.context),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def divided_by(self, other: Any) -> tuple:
        """Division: number1 / number2"""
        if isinstance(other, Number):
            if other.value == 0:
                return None, RTError(
                    other.pos_start,
                    other.pos_end,
                    c.ERRORS["division_by_zero"],
                    self.context,
                )

            return (
                Number(self.value / other.value).set_context(self.context),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def modulused_by(self, other: Any) -> tuple:
        """Modulus/Remainder: number1 % number2"""
        if isinstance(other, Number):
            if other.value == 0:
                return None, RTError(
                    other.pos_start,
                    other.pos_end,
                    c.ERRORS["modulus_by_zero"],
                    self.context,
                )

            return (
                Number(self.value % other.value).set_context(self.context),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def powered_by(self, other: Any) -> tuple:
        """Power Operator/Exponentiation: number1 ^ number2"""
        if isinstance(other, Number):
            return (
                Number(self.value**other.value).set_context(self.context),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_eq(self, other: Any) -> tuple:
        """== Equal To"""
        if isinstance(other, Number):
            return (
                Number(int(self.value == other.value)).set_context(
                    self.context
                ),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_ne(self, other: Any) -> tuple:
        """!= Not Equal To"""
        if isinstance(other, Number):
            return (
                Number(int(self.value != other.value)).set_context(
                    self.context
                ),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_lt(self, other: Any) -> tuple:
        """< Less Than"""
        if isinstance(other, Number):
            return (
                Number(int(self.value < other.value)).set_context(
                    self.context
                ),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_gt(self, other: Any) -> tuple:
        """> Greater Than"""
        if isinstance(other, Number):
            return (
                Number(int(self.value > other.value)).set_context(
                    self.context
                ),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_lte(self, other: Any) -> tuple:
        """<= Less Than Or Equal To"""
        if isinstance(other, Number):
            return (
                Number(int(self.value <= other.value)).set_context(
                    self.context
                ),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def get_comparison_gte(self, other: Any) -> tuple:
        """>= Greater Than Or Equal To"""
        if isinstance(other, Number):
            return (
                Number(int(self.value >= other.value)).set_context(
                    self.context
                ),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def anded_by(self, other: Any) -> tuple:
        """and Operator"""
        if isinstance(other, Number):
            return (
                Number(int(self.value and other.value)).set_context(
                    self.context
                ),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def ored_by(self, other: Any) -> tuple:
        """or Operator"""
        if isinstance(other, Number):
            return (
                Number(int(self.value or other.value)).set_context(
                    self.context
                ),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def notted(self) -> tuple:
        """not Operator"""
        return (
            Number(1 if self.value == 0 else 0).set_context(self.context),
            None,
        )

    def copy(self) -> Any:
        copy = Number(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def is_true(self) -> bool:
        return self.value != 0

    def __str__(self) -> str:
        return str(self.value)

    def __repr__(self) -> str:
        return str(self.value)


Number.none = Number(0)
Number.false = Number(0)
Number.true = Number(1)
Number.math_PI = Number(math.pi)


class String(Value):
    def __init__(self, value) -> None:
        super().__init__()
        self.value = value

    def added_to(self, other: Any) -> tuple:
        """String Concatenation: string1 + string2"""
        if isinstance(other, String):
            return (
                String(self.value + other.value).set_context(self.context),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def multplied_by(self, other: Any) -> tuple:
        """Repeat a String: string * number"""
        if isinstance(other, Number):
            return (
                String(self.value * other.value).set_context(self.context),
                None,
            )
        else:
            return None, Value.illegal_operation(self, other)

    def is_true(self) -> bool:
        return len(self.value) > 0

    def copy(self) -> Any:
        copy = String(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f'"{self.value}"'


class List(Value):
    def __init__(self, elements: Any) -> None:
        super().__init__()
        self.elements = elements

    def added_to(self, other: Any) -> tuple:
        """Append element: list + element"""
        new_list = self.copy()
        new_list.elements.append(other)
        return new_list, None

    def subtracted_by(self, other: Any) -> tuple:
        """Remove element using 'pop': list - number"""
        if isinstance(other, Number):
            new_list = self.copy()
            try:
                new_list.elements.pop(other.value)
                return new_list, None
            except IndexError:
                return None, RTError(
                    other.pos_start,
                    other.pos_end,
                    c.ERRORS["list_index_error"],
                    self.context,
                )
        else:
            return None, Value.illegal_operation(self, other)

    def multiplied_by(self, other: Any) -> tuple:
        """Extend - Concatenation of Lists: list1 * list2"""
        if isinstance(other, List):
            new_list = self.copy()
            new_list.elements.extend(other.elements)
            return new_list, None
        else:
            return None, Value.illegal_operation(self, other)

    def divided_by(self, other: Any) -> tuple:
        """Fetch element: list / number"""
        if isinstance(other, Number):
            try:
                return self.elements[other.value], None
            except IndexError:
                return None, RTError(
                    other.pos_start,
                    other.pos_end,
                    c.ERRORS["fetch_index_error"],
                    self.context,
                )
        else:
            return None, Value.illegal_operation(self, other)

    def copy(self) -> Any:
        copy = List(self.elements)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __str__(self) -> str:
        return ", ".join([str(x) for x in self.elements])

    def __repr__(self) -> str:
        return f'[{", ".join([repr(x) for x in self.elements])}]'


class BaseFunction(Value):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name or "<anonymous>"

    def set_context(self, context: Any = None) -> Any:
        """This code allows for 'true function closures'"""
        if hasattr(self, "context") and self.context:
            return self
        return super().set_context(context)

    def generate_new_context(self) -> Any:
        """This code enables true function closures"""
        new_context = Context(self.name, self.context, self.pos_start)
        new_context.symbol_table = SymbolTable(new_context.parent.symbol_table)
        return new_context

    def check_params(
        self, param_names: list, args: list
    ) -> RTResult | RTError:
        """
        Ensure that the number of parameters matches
        the function call's number of arguments
        """
        result = RTResult()  # initialise

        if len(args) > len(param_names):
            errormess = (
                f"{len(args) - len(param_names)} too many args "
                f"passed into {self}"
            )
            return result.failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    errormess,
                    self.context,
                )
            )

        if len(args) < len(param_names):
            errormess = (
                f"{len(param_names) - len(args)} too few args "
                f"passed into {self}"
            )
            return result.failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    errormess,
                    self.context,
                )
            )

        return result.success(None)

    def populate_params(
        self, param_names: list, args: list, execution_context: Any
    ) -> None:
        """Populate each parameter with its corresponding value"""
        for i in range(len(args)):
            param_name = param_names[i]
            param_value = args[i]
            param_value.set_context(execution_context)
            execution_context.symbol_table.set(param_name, param_value)

    def check_and_populate_params(
        self, param_names: list, args: list, execution_context: Any
    ) -> RTResult:
        """
        If the number of parameters and arguments match,
        then populate each parameter
        """
        result = RTResult()  # initialise
        # Check that the number of parameters
        # and the number of arguments match
        result.register(self.check_params(param_names, args))
        if result.should_return():
            # Error occurred i.e. the numbers don't match!
            return result

        # Populate the parameters with their corresponding values
        self.populate_params(param_names, args, execution_context)
        return result.success(None)


class Function(BaseFunction):
    def __init__(
        self,
        name: str,
        body_node: Any,
        arg_names: list,
        should_auto_return: bool,
    ) -> None:
        super().__init__(name)
        self.body_node = body_node
        self.arg_names = arg_names
        self.should_auto_return = should_auto_return

    def execute(self, args: list) -> RTResult:
        result = RTResult()  # initialise
        interpreter = Interpreter()  # initialise the Interpreter
        execution_context = self.generate_new_context()

        # Perform initial checks such as matching number of args
        # If checks are successful, populate parameters
        result.register(
            self.check_and_populate_params(
                self.arg_names, args, execution_context
            )
        )
        if result.should_return():
            # An error has occurred - the checks have failed
            return result

        # Execute the Function using the Interpreter
        thevalue = result.register(
            interpreter.visit(self.body_node, execution_context)
        )

        if result.should_return() and result.func_return_value is None:
            # An error has occurred or
            # a 'None' value must be returned at this point
            return result

        """
        Determine the 'return value'
        If 'self.should_auto_return' is true:
            This is an arrow function therefore
            set ret_value to whatever value is in 'thevalue'
        else:
            Multiline FUN
            set ret_value to Number.none

        However if after this assignment, 'ret_value' is falsy:
            then set ret_value to 'result.func_return_value'

        However if after this assignment, 'ret_value' is still falsy:
            then set ret_value to 'Number.none'
        """

        ret_value = (
            (thevalue if self.should_auto_return else None)
            or result.func_return_value
            or Number.none
        )
        return result.success(ret_value)

    def copy(self) -> Self:
        copy = Function(
            self.name, self.body_node, self.arg_names, self.should_auto_return
        )
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self) -> str:
        return f"<function {self.name}>"


class BuiltInFunction(BaseFunction):
    def __init__(self, name: str) -> None:
        super().__init__(name)

    def execute(self, args: list) -> RTResult:
        result = RTResult()
        execution_context = self.generate_new_context()

        method_name = f"execute_{self.name}"
        method = getattr(self, method_name, self.no_visit_method)

        result.register(
            self.check_and_populate_params(
                method.arg_names, args, execution_context
            )
        )
        if result.should_return():
            # An error has occurred
            return result

        return_value = result.register(method(execution_context))
        if result.should_return():
            # Either error, BREAK, CONTINUE or RETURN
            return result

        return result.success(return_value)

    def no_visit_method(self, node: Any, execution_context: Any) -> Exception:
        raise Exception(f"No execute_{self.name} method defined")

    def copy(self) -> Any:
        copy = BuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self) -> str:
        return f"<built-in function {self.name}>"

    #####################################

    def execute_print(self, execution_context: Any) -> RTResult:
        print(str(execution_context.symbol_table.get("value")))
        return RTResult().success(Number.none)

    execute_print.arg_names = ["value"]

    def execute_print_ret(self, execution_context: Any) -> RTResult:
        return RTResult().success(
            String(str(execution_context.symbol_table.get("value")))
        )

    execute_print_ret.arg_names = ["value"]

    def execute_input(self, execution_context: Any) -> RTResult:
        text = input()
        return RTResult().success(String(text))

    execute_input.arg_names = []

    def execute_input_int(self, execution_context: Any) -> RTResult:
        while True:
            text = input()
            try:
                number = int(text)
                break
            except ValueError:
                print(f"'{text}' must be an integer. Try again!")
        return RTResult().success(Number(number))

    execute_input_int.arg_names = []

    def execute_clear(self, execution_context: Any) -> RTResult:
        os.system("cls" if os.name == "nt" else "cls")
        return RTResult().success(Number.none)

    execute_clear.arg_names = []

    def execute_is_number(self, execution_context: Any) -> RTResult:
        is_number = isinstance(
            execution_context.symbol_table.get("value"), Number
        )
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_number.arg_names = ["value"]

    def execute_is_string(self, execution_context: Any) -> RTResult:
        is_number = isinstance(
            execution_context.symbol_table.get("value"), String
        )
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_string.arg_names = ["value"]

    def execute_is_list(self, execution_context: Any) -> RTResult:
        is_number = isinstance(
            execution_context.symbol_table.get("value"), List
        )
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_list.arg_names = ["value"]

    def execute_is_function(self, execution_context: Any) -> RTResult:
        is_number = isinstance(
            execution_context.symbol_table.get("value"), BaseFunction
        )
        return RTResult().success(Number.true if is_number else Number.false)

    execute_is_function.arg_names = ["value"]

    def execute_append(self, execution_context: Any) -> RTResult:
        """Mutable Append element: append(list, value)"""
        list_ = execution_context.symbol_table.get("list")
        value = execution_context.symbol_table.get("value")

        if not isinstance(list_, List):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    c.ERRORS["arg1_list_expected"],
                    execution_context,
                )
            )

        list_.elements.append(value)
        return RTResult().success(Number.none)

    execute_append.arg_names = ["list", "value"]

    def execute_pop(self, execution_context: Any) -> RTResult:
        """Mutable Remove/Pop element: pop(list, index)"""
        list_ = execution_context.symbol_table.get("list")
        index = execution_context.symbol_table.get("index")

        if not isinstance(list_, List):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    c.ERRORS["arg1_list_expected"],
                    execution_context,
                )
            )

        if not isinstance(index, Number):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    c.ERRORS["arg2_number_expected"],
                    execution_context,
                )
            )

        try:
            element = list_.elements.pop(index.value)
        except IndexError:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    c.ERRORS["list_index_error"],
                    execution_context,
                )
            )
        return RTResult().success(element)

    execute_pop.arg_names = ["list", "index"]

    def execute_extend(self, execution_context: Any) -> RTResult:
        """Mutable Extend - Concatenation of Lists: extend(listA, listB)"""
        listA = execution_context.symbol_table.get("listA")
        listB = execution_context.symbol_table.get("listB")

        if not isinstance(listA, List):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    c.ERRORS["arg1_list_expected"],
                    execution_context,
                )
            )

        if not isinstance(listB, List):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    c.ERRORS["arg2_list_expected"],
                    execution_context,
                )
            )

        listA.elements.extend(listB.elements)
        return RTResult().success(Number.none)

    execute_extend.arg_names = ["listA", "listB"]

    def execute_len(self, execution_context: Any) -> RTResult:
        """Length of list: len(list)"""
        list_ = execution_context.symbol_table.get("list")

        if not isinstance(list_, List):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    c.ERRORS["arg_list_expected"],
                    execution_context,
                )
            )

        return RTResult().success(Number(len(list_.elements)))

    execute_len.arg_names = ["list"]

    def execute_run(self, execution_context: Any) -> RTResult:
        """
        Run File Script: run(filename)
        run() is deprecated. Use 'IMPORT' instead
        """
        filename = execution_context.symbol_table.get("filename")

        if not isinstance(filename, String):
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    c.ERRORS["arg2_string_expected"],
                    execution_context,
                )
            )

        print("WARNING: run() is deprecated. Use 'IMPORT' instead")

        filename = filename.value

        try:
            with open(filename, "r") as f:
                script = f.read()
        except Exception as e:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to load script "{filename}"\n' + str(e),
                    execution_context,
                )
            )

        _, error = run(filename, script)

        if error:
            return RTResult().failure(
                RTError(
                    self.pos_start,
                    self.pos_end,
                    f'Failed to finish executing script "{filename}"\n'
                    + error.as_string(),
                    execution_context,
                )
            )

        return RTResult().success(Number.none)

    execute_run.arg_names = ["filename"]


BuiltInFunction.print = BuiltInFunction("print")
BuiltInFunction.print_ret = BuiltInFunction("print_ret")
BuiltInFunction.input = BuiltInFunction("input")
BuiltInFunction.input_int = BuiltInFunction("input_int")
BuiltInFunction.clear = BuiltInFunction("clear")
BuiltInFunction.is_number = BuiltInFunction("is_number")
BuiltInFunction.is_string = BuiltInFunction("is_string")
BuiltInFunction.is_list = BuiltInFunction("is_list")
BuiltInFunction.is_function = BuiltInFunction("is_function")
BuiltInFunction.append = BuiltInFunction("append")
BuiltInFunction.pop = BuiltInFunction("pop")
BuiltInFunction.extend = BuiltInFunction("extend")
BuiltInFunction.len = BuiltInFunction("len")
BuiltInFunction.run = BuiltInFunction("run")

#######################################
# CONTEXT
#######################################


class Context:
    def __init__(
        self,
        display_name: str,
        parent: Any = None,
        parent_entry_pos: Optional[int] = None,
    ) -> None:
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_pos = parent_entry_pos
        self.symbol_table = None


#######################################
# SYMBOL TABLE
#######################################


class SymbolTable:
    def __init__(self, parent: Any = None) -> None:
        self.symbols: dict = {}
        self.parent = parent

    def get(self, name: str) -> Any:
        """
        Recursively using the 'parent' determine
        the value of the variable
        Return 'None' if no such value is found
        """
        value = self.symbols.get(name, None)
        if value is None and self.parent:
            return self.parent.get(name)
        return value

    def set(self, name: str, value: Any) -> None:
        """Set the named variable to this value"""
        self.symbols[name] = value

    def remove(self, name: str) -> None:
        """Removed the named variable from the symbol table"""
        del self.symbols[name]


#######################################
# INTERPRETER
#######################################


class Interpreter:
    def visit(self, node: Any, context: Context) -> Any:
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, context)

    def no_visit_method(self, node: Any, context: Context) -> Exception:
        raise Exception(f"No visit_{type(node).__name__} method defined")

    ###################################

    def visit_NumberNode(self, node: Any, context: Context) -> RTResult:
        return RTResult().success(
            Number(node.token.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_StringNode(self, node: Any, context: Context) -> RTResult:
        return RTResult().success(
            String(node.token.value)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_ListNode(self, node: Any, context: Context) -> RTResult:
        result = RTResult()
        elements = []

        for element_node in node.element_nodes:
            elements.append(result.register(self.visit(element_node, context)))
            if result.should_return():
                return result

        # List successfully created
        return result.success(
            List(elements)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_VarAccessNode(self, node: Any, context: Context) -> RTResult:
        result = RTResult()  # Initialise
        var_name = node.var_name_token.value
        value = context.symbol_table.get(var_name)

        if not value:
            return result.failure(
                RTError(
                    node.pos_start,
                    node.pos_end,
                    f"'{var_name}' is not defined",
                    context,
                )
            )

        value = (
            value.copy()
            .set_pos(node.pos_start, node.pos_end)
            .set_context(context)
        )
        return result.success(value)

    def visit_VarAssignNode(self, node: Any, context: Context) -> RTResult:
        result = RTResult()  # Initialise
        var_name = node.var_name_token.value
        value = result.register(self.visit(node.value_node, context))
        if result.should_return():
            return result

        # Set the variable to this value i.e. VAR = VALUE
        context.symbol_table.set(var_name, value)
        return result.success(value)

    def visit_BinOpNode(self, node: Any, context: Context) -> RTResult:
        result = RTResult()  # Initialise
        left = result.register(self.visit(node.left_node, context))
        if result.should_return():
            return result
        right = result.register(self.visit(node.right_node, context))
        if result.should_return():
            return result

        if node.operator_token.type == TOKEN_TYPE_PLUS:
            calc_result, error = left.added_to(right)
        elif node.operator_token.type == TOKEN_TYPE_MINUS:
            calc_result, error = left.subtracted_by(right)
        elif node.operator_token.type == TOKEN_TYPE_MULTIPLY:
            calc_result, error = left.multiplied_by(right)
        elif node.operator_token.type == TOKEN_TYPE_DIVIDE:
            calc_result, error = left.divided_by(right)
        elif node.operator_token.type == TOKEN_TYPE_MODULUS:
            calc_result, error = left.modulused_by(right)
        elif node.operator_token.type == TOKEN_TYPE_POWER:
            calc_result, error = left.powered_by(right)
        elif node.operator_token.type == TOKEN_TYPE_EQUAL_TO:
            calc_result, error = left.get_comparison_eq(right)
        elif node.operator_token.type == TOKEN_TYPE_NOT_EQUAL_TO:
            calc_result, error = left.get_comparison_ne(right)
        elif node.operator_token.type == TOKEN_TYPE_LESS_THAN:
            calc_result, error = left.get_comparison_lt(right)
        elif node.operator_token.type == TOKEN_TYPE_GREATER_THAN:
            calc_result, error = left.get_comparison_gt(right)
        elif node.operator_token.type == TOKEN_TYPE_LESS_THAN_EQUAL_TO:
            calc_result, error = left.get_comparison_lte(right)
        elif node.operator_token.type == TOKEN_TYPE_GREATER_THAN_EQUAL_TO:
            calc_result, error = left.get_comparison_gte(right)
        elif node.operator_token.matches(TOKEN_TYPE_KEYWORD, "AND"):
            calc_result, error = left.anded_by(right)
        elif node.operator_token.matches(TOKEN_TYPE_KEYWORD, "OR"):
            calc_result, error = left.ored_by(right)

        if error:
            return result.failure(error)
        else:
            return result.success(
                calc_result.set_pos(node.pos_start, node.pos_end)
            )

    def visit_UnaryOpNode(self, node: Any, context: Context) -> RTResult:
        result = RTResult()  # Initialise
        number = result.register(self.visit(node.node, context))
        if result.should_return():
            return result

        error = None

        if node.operator_token.type == TOKEN_TYPE_MINUS:
            # -x
            number, error = number.multiplied_by(Number(-1))
        elif node.operator_token.matches(TOKEN_TYPE_KEYWORD, "NOT"):
            # NOT x
            number, error = number.notted()

        if error:
            return result.failure(error)
        else:
            return result.success(number.set_pos(node.pos_start, node.pos_end))

    def visit_IfNode(self, node: Any, context: Context) -> RTResult:
        """Execute the IF/ELIF/ELSE expression/statement"""
        result = RTResult()  # Initialise

        """
        node.cases is a list of nodes depicting IF condition THEN body
        [[cond1, body1], [cond2, body2], ... [condN, bodyN]]
        So, try every condition from 1 to N
        Until a 'condition' is true
        Then execute the corresponding body and return its value
        """

        for condition, expr, should_return_none in node.cases:
            condition_value = result.register(self.visit(condition, context))
            if result.should_return():
                return result

            if condition_value.is_true():
                expr_value = result.register(self.visit(expr, context))
                if result.should_return():
                    return result

                # Return the value - Number.none if no value
                return result.success(
                    Number.none if should_return_none else expr_value
                )

        """
        None of the conditions are true therefore if an ELSE expr/statement
        is present, execute it
        """
        if node.else_case:
            expr, should_return_none = node.else_case
            expr_value = result.register(self.visit(expr, context))
            if result.should_return():
                # Return the result at this point
                return result

            # Return the ELSE value - Number.none if no value
            return result.success(
                Number.none if should_return_none else expr_value
            )

        # There is NO ELSE therefore return Number.none
        return result.success(Number.none)

    def visit_ForNode(self, node: Any, context: Context) -> RTResult:
        """Execute the FOR expression/statement"""
        result = RTResult()  # Initialise
        elements = []

        # Determine the FOR's Start value
        start_value = result.register(
            self.visit(node.start_value_node, context)
        )
        if result.should_return():
            return result

        # Determine the FOR's TO/End value
        end_value = result.register(self.visit(node.end_value_node, context))
        if result.should_return():
            return result

        if node.step_value_node:
            # Determine the FOR's STEP value
            step_value = result.register(
                self.visit(node.step_value_node, context)
            )
            if result.should_return():
                return result
        else:
            # Default STEP value is 1
            step_value = Number(1)

        # Initialise with the FOR's Start value
        i = start_value.value

        # Execute the FOR loop
        while True:
            condition = (
                i < end_value.value
                if step_value.value >= 0
                else i > end_value.value
            )

            # Continue the FOR Loop?
            if not condition:
                break

            # Yes! Update the FOR variable
            context.symbol_table.set(node.var_name_token.value, Number(i))
            i += step_value.value

            # Evaluate the FOR body
            value = result.register(self.visit(node.body_node, context))

            # Should the loop be ended because of an error or a RETURN?
            if (
                result.should_return()
                and result.loop_should_continue is False
                and result.loop_should_break is False
            ):
                return result

            # Has a CONTINUE Loop occurred?
            if result.loop_should_continue:
                continue

            # Has a BREAK Loop occurred?
            if result.loop_should_break:
                break

            # Append the newly evaluated FOR value
            elements.append(value)

        return result.success(
            Number.none
            if node.should_return_none  # Indicates a FOR statement
            else List(elements)  # return all the FOR values
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_WhileNode(self, node: Any, context: Context) -> RTResult:
        """Execute the WHILE expression/statement"""
        result = RTResult()  # Initialise
        elements = []

        # Execute the WHILE loop
        while True:
            condition = result.register(
                self.visit(node.condition_node, context)
            )
            if result.should_return():
                return result

            # Continue the WHILE Loop?
            if not condition.is_true():
                break

            # Evaluate the WHILE body
            value = result.register(self.visit(node.body_node, context))

            # Should the loop be ended because of an error or a RETURN?
            if (
                result.should_return()
                and result.loop_should_continue is False
                and result.loop_should_break is False
            ):
                return result

            # Has a CONTINUE Loop occurred?
            if result.loop_should_continue:
                continue

            # Has a BREAK Loop occurred?
            if result.loop_should_break:
                break

            # Append the newly evaluated WHILE value
            elements.append(value)

        return result.success(
            Number.none
            if node.should_return_none  # Indicates a WHILE statement
            else List(elements)  # return all the WHILE values
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

    def visit_FuncDefNode(self, node: Any, context: Context) -> RTResult:
        """Execute the FUN expression/statement"""
        result = RTResult()  # Initialise

        # Determine 'func_name' depending on whether the function is anonymous
        # The 'None' value indicates an anonymous function
        func_name = node.var_name_token.value if node.var_name_token else None
        body_node = node.body_node
        arg_names = [arg_name.value for arg_name in node.arg_name_tokens]
        func_value = (
            Function(func_name, body_node, arg_names, node.should_auto_return)
            .set_context(context)
            .set_pos(node.pos_start, node.pos_end)
        )

        if node.var_name_token:
            # Function definition assigned to 'func_name'
            # if not anonymous
            # This allows functions to be first class objects
            context.symbol_table.set(func_name, func_value)

        return result.success(func_value)

    def visit_CallNode(self, node: Any, context: Context) -> RTResult:
        """Execute a Call of a FUNction"""
        result = RTResult()  # Initialise
        args = []

        # Determine the Function Name
        value_to_call = result.register(self.visit(node.node_to_call, context))
        if result.should_return():
            return result
        value_to_call = value_to_call.copy().set_pos(
            node.pos_start, node.pos_end
        )

        # Determine the arguments of the function
        for arg_node in node.arg_nodes:
            args.append(result.register(self.visit(arg_node, context)))
            if result.should_return():
                return result

        # Execute the Function Call
        return_value = result.register(value_to_call.execute(args))
        if result.should_return():
            return result

        # Determine the return value
        return_value = (
            return_value.copy()
            .set_pos(node.pos_start, node.pos_end)
            .set_context(context)
        )

        # Return the Function's return value
        return result.success(return_value)

    def visit_ReturnNode(self, node: Any, context: Context) -> RTResult:
        """
        Execute the RETURN expression
        If RETURN is followed by an expression
        Evaluate this expression and return its value

        If no expression, return Number.none

        This also ensures that a RETURN from a Multiline Function
        returns 'Number.none'
        """
        result = RTResult()  # Initialise

        if node.node_to_return:
            # RETURN expression
            value = result.register(self.visit(node.node_to_return, context))
            if result.should_return():
                # Return the evaluated expression
                # This also handles any errors occurring
                return result
        else:
            # RETURN followed by no expression
            # Therefore represent that no value was returned
            value = Number.none

        # Return the determined return value
        return result.success_return(value)

    def visit_ContinueNode(self, node: Any, context: Context) -> RTResult:
        """Execute the CONTINUE"""
        return RTResult().success_continue()

    def visit_BreakNode(self, node: Any, context: Context) -> RTResult:
        """Execute the BREAK"""
        return RTResult().success_break()

    """ Allows imports of scripts whilst executing the main script """

    def visit_ImportNode(self, node: Any, context: Context) -> RTResult:
        result = RTResult()
        filepath = result.register(self.visit(node.string_node, context))

        try:
            with open(filepath.value, "r") as f:
                filename = filepath.value.split("/")[-1]
                code = f.read()
        except FileNotFoundError:
            return result.failure(
                RTError(
                    node.string_node.pos_start.copy(),
                    node.string_node.pos_end.copy(),
                    f"Can't find file '{filepath.value}'",
                    context,
                )
            )

        run_result, error = run(
            filename, code, context, node.pos_start.copy(), return_result=True
        )
        if error:
            return RTResult().failure(
                RTError(
                    node.string_node.pos_start.copy(),
                    node.string_node.pos_end.copy(),
                    f'Failed to IMPORT script "{filename}"\n'
                    + error.as_string(),
                    context,
                )
            )

        result.register(run_result)
        if result.error:
            return result

        # This is the value of the IMPORT statement
        return result.success(Number.none)


#######################################
# RUN
#######################################


# Set up all the BuiltIn constants and functions
global_symbol_table = SymbolTable()
global_symbol_table.set("NONE", Number.none)
global_symbol_table.set("FALSE", Number.false)
global_symbol_table.set("TRUE", Number.true)
global_symbol_table.set("MATH_PI", Number.math_PI)
global_symbol_table.set("PRINT", BuiltInFunction.print)
global_symbol_table.set("PRINT_RET", BuiltInFunction.print_ret)
global_symbol_table.set("INPUT", BuiltInFunction.input)
global_symbol_table.set("INPUT_INT", BuiltInFunction.input_int)
global_symbol_table.set("CLEAR", BuiltInFunction.clear)
global_symbol_table.set("CLS", BuiltInFunction.clear)
global_symbol_table.set("IS_NUM", BuiltInFunction.is_number)
global_symbol_table.set("IS_STR", BuiltInFunction.is_string)
global_symbol_table.set("IS_LIST", BuiltInFunction.is_list)
global_symbol_table.set("IS_FUN", BuiltInFunction.is_function)
global_symbol_table.set("APPEND", BuiltInFunction.append)
global_symbol_table.set("POP", BuiltInFunction.pop)
global_symbol_table.set("EXTEND", BuiltInFunction.extend)
global_symbol_table.set("LEN", BuiltInFunction.len)
global_symbol_table.set("RUN", BuiltInFunction.run)


def run(
    filename: str,
    text: str,
    context: Optional[Context] = None,
    entry_pos: Optional[int] = None,
    return_result: bool = False,
) -> tuple:
    """'RUN' Expanded to allow each script to have its own 'context'"""
    # Generate tokens
    lexer = Lexer(filename, text)
    tokens, error = lexer.make_tokens()
    if error:
        return None, error

    # Generate AST
    parser = Parser(tokens)
    ast = parser.parse()
    if ast.error:
        return None, ast.error

    # Run program
    interpreter = Interpreter()
    context = Context("<program>", context, entry_pos)
    if context.parent is None:
        context.symbol_table = global_symbol_table
    else:
        context.symbol_table = context.parent.symbol_table

    result = interpreter.visit(ast.node, context)
    if return_result:
        # The value of run()
        return result, None

    return result.value, result.error
