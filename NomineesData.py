class NomineesData:

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

        self.nom_id = info_dict.get('nominatorid', None)
        self.pillar_id = info_dict.get('pillarid', None)
        self.note = info_dict.get('note', None)

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
        return 'NomineesData: NominatorID:{0.nom_id} NominatedUser:{0.pillar_id} Note:{0.note}'.format(self)

    def __bool__(self):
        """
        Override boolean to check if any values are set, if yes then return True, else False, where false is an empty
        class.

        :rtype: bool
        """
        return any([value for key, value in vars(self).items() if value])
