class CarrierData:

    def __init__(self, info_dict=None):
        """
        Class represents a carrier object as returned from the database.
        """
        if not info_dict:
            info_dict = dict()

        self.carrier_long_name = info_dict.get('longname', None)
        self.carrier_short_name = info_dict.get('shortname', None)
        self.discord_channel = info_dict.get('discordchannel', None)
        self.channel_id = info_dict.get('channelid', None)
        self.carrier_identifier = info_dict.get('cid', None)
        self.pid = info_dict.get('p_ID', None)

    def to_dictionary(self):
        """
        Formats the carrier data into a dictionary for easy access.

        :returns: A dictionary representation for the carrier data.
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
        return 'CarrierData: CarrierLongName:{0.carrier_long_name} CarrierShortName:{0.carrier_short_name} ' \
               'CarrierIdentifier:{0.carrier_identifier} DiscordChannel:{0.discord_channel} ' \
               'DiscordChannelID:{0.channel_id} CarrierPid:{0.pid}'.format(self)

    def __bool__(self):
        """
        Override boolean to check if any values are set, if yes then return True, else False, where false is an empty
        class.

        :rtype: bool
        """
        return any([value for key, value in vars(self).items() if value])
