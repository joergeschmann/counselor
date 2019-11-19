class Operators:
    OPERATOR_EQUALITY = "=="
    OPERATOR_INEQUALITY = "!="

    OPERATOR_EMPTY = "empty"
    OPERATOR_NOT_EMPTY = "not empty"

    OPERATOR_IN = "in"
    OPERATOR_NOT_IN = "not in"
    OPERATOR_CONTAINS = "contains"
    OPERATOR_NOT_CONTAINS = "not contains"


class Fields:
    FIELD_TAGS = "Tags"
    FIELD_META = "Meta"


class KeyValuePair:
    """Simple representation of a key value pair.
    """

    def __init__(self, key: str, value: str):
        self.key = key
        self.value = value


class Filter:
    """Filter to provide simple search functionality in Consul.
    """

    def __init__(self, selector: str, operator: str, value: str):
        self.selector = selector
        self.operator = operator
        self.value = value

    @staticmethod
    def new_tag_filter(operator: str, value: str):
        return Filter(selector=Fields.FIELD_TAGS, operator=operator, value=value)

    @staticmethod
    def new_meta_filter(key: str, operator: str, value: str):
        return Filter(selector=Fields.FIELD_META + "." + key, operator=operator, value=value)

    def as_expression(self) -> str:
        """
        // Equality & Inequality checks
        <Selector> == <Value>
        <Selector> != <Value>

        // Emptiness checks
        <Selector> is empty
        <Selector> is not empty

        // Contains checks or Substring Matching
        <Value> in <Selector>
        <Value> not in <Selector>
        <Selector> contains <Value>
        <Selector> not contains <Value>
        """

        if self.operator == Operators.OPERATOR_EQUALITY or self.operator == Operators.OPERATOR_INEQUALITY:
            return "{} {} {}".format(self.selector, self.operator, self.value)

        elif self.operator == Operators.OPERATOR_EMPTY or self.operator == Operators.OPERATOR_NOT_EMPTY:
            return "{} {} {}".format(self.selector, self.operator, self.value)

        elif self.operator == Operators.OPERATOR_IN or self.operator == Operators.OPERATOR_NOT_IN:
            return "{} {} {}".format(self.value, self.operator, self.selector)

        elif self.operator == Operators.OPERATOR_CONTAINS or self.operator == Operators.OPERATOR_NOT_CONTAINS:
            return "{} {} {}".format(self.selector, self.operator, self.value)
