# image manipulation and output for mission generator and carrier_image command
import tempfile
from PIL import Image, ImageFont, ImageDraw
import ptn.missionalertbot.constants as constants


# function to overlay carrier image with background template
async def _overlay_mission_image(carrier_data):
    print("Called mission image overlay function")
    """
    template:       the background image with logo, frame elements etc
    carrier_image:  the inset image optionally created by the Carrier Owner
    """
    template = Image.open("template.png")
    carrier_image = Image.open(f"images/{carrier_data.carrier_short_name}.png")   
    template.paste(carrier_image, (47,13))
    return template


# function to create image for loading
async def create_carrier_mission_image(carrier_data, commodity, system, station, profit, pads, demand, mission_type):
    print("Called mission image generator")
    """
    Builds the carrier image and returns the relative path.
    """

    template = await _overlay_mission_image(carrier_data)

    image_editable = ImageDraw.Draw(template)
    
    mission_action = 'LOADING' if mission_type == 'load' else 'UNLOADING'
    image_editable.text((46, 304), "PILOTS TRADE NETWORK", (255, 255, 255), font=constants.TITLE_FONT)
    image_editable.text((46, 327), f"CARRIER {mission_action} MISSION", (191, 53, 57), font=constants.TITLE_FONT)
    image_editable.text((46, 366), "FLEET CARRIER " + carrier_data.carrier_identifier, (0, 217, 255), font=constants.REG_FONT)
    image_editable.text((46, 382), carrier_data.carrier_long_name, (0, 217, 255), font=constants.NAME_FONT)
    image_editable.text((46, 439), "COMMODITY:", (255, 255, 255), font=constants.FIELD_FONT)
    image_editable.text((170, 439), commodity.name.upper(), (255, 255, 255), font=constants.NORMAL_FONT)
    image_editable.text((46, 477), "SYSTEM:", (255, 255, 255), font=constants.FIELD_FONT)
    image_editable.text((170, 477), system.upper(), (255, 255, 255), font=constants.NORMAL_FONT)
    image_editable.text((46, 514), "STATION:", (255, 255, 255), font=constants.FIELD_FONT)
    image_editable.text((170, 514), f"{station.upper()} ({pads.upper()} pads)", (255, 255, 255), font=constants.NORMAL_FONT)
    image_editable.text((46, 552), "PROFIT:", (255, 255, 255), font=constants.FIELD_FONT)
    image_editable.text((170, 552), f"{profit}k per unit, {demand} units", (255, 255, 255), font=constants.NORMAL_FONT)
    
    # Check if this will work fine, we might need to delete=False and clean it ourselves
    result_name = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    print(f'Saving temporary mission file for carrier: {carrier_data.carrier_long_name} to: {result_name.name}')
    template.save(result_name.name)
    return result_name.name



