class TopologicalSortException(Exception):
    """
    Исключение для ошибок топологической сортировки.
    """

    def __init__(self, message=None, fields=None):
        self.message = message
        self.fields = fields
        super().__init__(self.message)
    
    def __str__(self):
        return f"TopologicalSortException: {self.message} (fields: {', '.join(self.fields) if self.fields else 'None'})"
