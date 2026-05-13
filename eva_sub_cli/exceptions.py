class NoVcfsFoundException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class InvalidFileTypeError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class MetadataTemplateVersionException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class MetadataTemplateVersionNotFoundException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SubmissionNotFoundException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SubmissionStatusException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SubmissionUploadException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
