class WebhookData:

    def __init__(self, info_dict=None):
        """
        Class represents a nominee object as returned from the database.

        :param sqlite.Row info_dict: A single row from the sqlite query.
        """
        if info_dict:
            # Convert the sqlite3.Row object to a dictionary
            info_dict = dict(info_dict)
        else:
            info_dict = dict()

        self.webhook_owner_id = info_dict.get('webhook_owner_id', None)
        self.webhook_url = info_dict.get('webhook_url', None)
        self.webhook_name = info_dict.get('webhook_name', None)

    def to_dictionary(self):
        """
        Formats the nominee data into a dictionary for easy access.

        :returns: A dictionary representation for the nominee data.
        :rtype: dict
        """
        response = {}
        for key, value in vars(self).items():
            if value is not None:
                response[key] = value
        return response

    def __str__(self):
        """
        Overloads str to return a readable object

        :rtype: str
        """
        return 'NomineesData: OwnerID:{0.webhook_owner_id} WebHookURL:{0.webhook_url} WebHookName:{0.webhook_name}'.format(self)

    def __bool__(self):
        """
        Override boolean to check if any values are set, if yes then return True, else False, where false is an empty
        class.

        :rtype: bool
        """
        return any([value for key, value in vars(self).items() if value])
