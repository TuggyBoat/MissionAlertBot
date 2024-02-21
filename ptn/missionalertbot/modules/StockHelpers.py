"""
A module for helper functions specifically for the Stock Tracker function.

Depends on: constants, ErrorHandler

"""

# import libraries
import json
from bs4 import BeautifulSoup
import requests

# import discord.py

# import local classes

# import local constants
import ptn.missionalertbot.constants as constants
from ptn.missionalertbot.constants import bot

# import local modules
from ptn.missionalertbot.modules.ErrorHandler import CommandChannelError, CommandRoleError, CustomError, GenericError, on_generic_error

def load_carrier_data(CARRIERS):
    # unpack carrier data if we have it, or start fresh
    print(f'Loading Carrier Data.')
    try:
        FCDATA = json.loads(CARRIERS)
    except:
        FCDATA = convert_carrier_data()
    return FCDATA


def save_carrier_data(FCDATA):
    print(f'Saving Carrier Data.')
    #dotenv_file = find_dotenv()
    CARRIERS = json.dumps(FCDATA)
    set_key(carrierdb, "FLEET_CARRIERS", CARRIERS)



def inara_find_fc_system(fcid):
    #print("Searching inara for carrier %s" % ( fcid ))
    URL = "https://inara.cz/station/?search=%s" % ( fcid )
    try:
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, "html.parser")
        results = soup.find_all("div", class_="maincontent1")
        carrier = results[0].find("h3", class_="standardcase").find("a", href=True)
        system = results[0].find("span", class_="uppercase").find("a", href=True).text
        if fcid == carrier.text[-8:-1]:
            #print("Carrier: %s (stationid %s) is at system: %s" % (carrier.text[:-3], stationid['href'][9:-1], system.text))
            return {'system': system, 'stationid': carrier['href'][9:-1], 'full_name': carrier.text }
        else:
            print("Could not find exact match, aborting inara search")
            return False
    except Exception as e:
        print("No results from inara for %s, aborting search. Error: %s" % ( fcid, e ))
        return False


def edsm_find_fc_system(fcid):
    #print("Searching edsm for carrier %s" % ( fcid ))
    URL = "https://www.edsm.net/en/search/stations/index/name/%s/sortBy/distanceSol/type/31" % ( fcid )
    try:
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, "html.parser")
        results = soup.find("table", class_="table table-hover").find("tbody").find_all("a")
        carrier = results[0].get_text()
        system = results[1].get_text()
        market_updated = results[6].find("i").attrs.get("title")[27:]
        if fcid == carrier:
            #print("Carrier: %s is at system: %s" % (carrier, system))
            return {'system': system, 'market_updated': market_updated}
        else:
            #print("Could not find exact match, aborting inara search")
            return False
    except:
        print("No results from edsm for %s, aborting search." % fcid)
        return False


def inara_fc_market_data(fcid):
    #print("Searching inara market data for station: %s (%s)" % ( stationid, fcid ))
    try:
        URL = "https://inara.cz/station/?search=%s" % ( fcid )
        page = requests.get(URL)
        soup = BeautifulSoup(page.content, "html.parser")
        results = soup.find_all("div", class_="maincontent1")
        carrier = results[0].find("h3", class_="standardcase").find("a", href=True).text
        system = results[0].find("span", class_="uppercase").find("a", href=True).text
        updated = soup.find("div", text="Market update").next_sibling.get_text()
        results = soup.find("div", class_="mainblock maintable")
        rows = results.find("table", class_="tablesorterintab").find("tbody").find_all("tr")
        marketdata = []
        for row in rows:
            rowclass = row.attrs.get("class") or []
            if "subheader" in rowclass:
                continue
            cells = row.find_all("td")
            rn = cells[0].get_text()
            commodity = {
                            'id': rn,
                            'name': rn,
                            'sellPrice': cells[1].get_text(),
                            'buyPrice': cells[2].get_text(),
                            'demand': cells[3].get_text().replace('-', '0'),
                            'stock': cells[4].get_text().replace('-', '0')
                        }
            marketdata.append(commodity)
        data = {}
        data['name'] = system
        data['full_name'] = carrier
        data['sName'] = fcid
        data['market_updated'] = updated
        data['commodities'] = marketdata
        return data
    except Exception as e:
        print("Exception getting inara data for carrier: %s" % fcid)
        #traceback.print_exc()
        return False


def get_fccode(fcname):
    # TODO support ;stock command here, namely fcdata
    fcname = fcname.lower()
    #fcdata = False
    fccode = False
    for fc_code, fc_data in FCDATA.items():
        if fc_data['FCName'] == fcname:
            #fcdata = fc_data
            fccode = fc_code
            break
    return fccode


def get_fc_stock(fccode, source='edsm'):
    if source == 'inara':
        stn_data = inara_fc_market_data(fccode)
        if not stn_data:
            return False
    else:
        pmeters = {'marketId': FCDATA[fccode]['FCMid']}
        r = requests.get('https://www.edsm.net/api-system-v1/stations/market',params=pmeters)
        stn_data = r.json()

        edsm_search = edsm_find_fc_system(fccode)
        if edsm_search:
            stn_data['market_updated'] = edsm_search['market_updated']
        else:
            stn_data['market_updated'] = "Unknown"
        stn_data['full_name'] = False
    return stn_data


def chunk(chunk_list, max_size=10):
    """
    Take an input list, and an expected max_size.

    :returns: A chunked list that is yielded back to the caller
    :rtype: iterator
    """
    for i in range(0, len(chunk_list), max_size):
        yield chunk_list[i:i + max_size]