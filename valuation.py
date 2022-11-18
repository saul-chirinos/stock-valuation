import sys
import time
import warnings

import numpy as np
import numpy_financial as npf
import pandas as pd
import yahoo_fin.stock_info as si
from forex_python.converter import CurrencyRates

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

pd.set_option('display.float_format', lambda x: '%.2f' % x)
warnings.filterwarnings('ignore')

PATH = 'C:\\Program Files\chromedriver.exe'
WINDOW_SIZE = '1920,1080'

OPTIONS = Options()
OPTIONS.add_argument("--headless")
OPTIONS.add_argument("--window-size=%s" % WINDOW_SIZE)
OPTIONS.add_experimental_option('excludeSwitches', ['enable-logging'])

# Which index to select while going through each row in the tables
# TODO: Shorten code (DRY principle)
INDEXES = {
    'years' : {
        10: [-1, -4, -6, -8, -11],
        7: [-1, -4, -6, -8],
        5: [-1, -4, -6],
        3: [-1, -4],
        0: [-1]
    },
    'data': {
        10: [-12, -9, -7, -5, -2],
        7: [-9, -7, -5, -2],
        5: [-7, -5, -2],
        3: [-5, -2],
        0: [-2]
    }
}

ROOT_XPATH = '//*[@id="__layout"]/div/div/div[2]/div[3]/main/div[2]/div/div/div[1]/sal-components/div/sal-components-stocks-valuation/div/div[2]/div/div/div'
DIVS = '/div/div/div/div/div'
XPATHS = {
    'growth_years': ROOT_XPATH+'[3]'+DIVS+'/div[1]/table/tbody/tr[1]',
    'growth': ROOT_XPATH+'[3]'+DIVS+'/div[1]/table/tbody',
    'op_eff_years': ROOT_XPATH+'[4]'+DIVS+'[1]/table/thead',
    'op_eff': ROOT_XPATH+'[4]'+DIVS+'[1]/table/tbody',
    'fin_health_years': ROOT_XPATH+'[5]'+DIVS+'/div[1]/table/tbody/tr[5]',
    'fin_health': ROOT_XPATH+'[5]'+DIVS+'/div[1]/table/tbody/tr[5]',
    'cash_flow_years': ROOT_XPATH+'[6]'+DIVS+'/div[1]/table/tbody/tr[6]',
    'cash_flow': ROOT_XPATH+'[6]'+DIVS+'/div[1]/table/tbody/tr[6]'
}

LOCATORS = [
    'keyStatsgrowthTable',
    'keyStatsOperatingAndEfficiency',
    'keyStatsfinancialHealth',
    'keyStatscashFlow',
]

MARR = 0.15
EPS_GR = 0.1
EPS_GR_LIM = 0.25
TICKER_BRIDGE = {
    'BRK.B': 'BRK-B'
}

NA = '—'


S = Service(PATH)
# DRIVER = Chrome(service=S)
DRIVER = Chrome(service=S, options=OPTIONS)


def check_length(rows: list, years: bool = False):
    # TODO: Look into case statements in python, maybe they will make
    # the code in check_years and check_rows more clean and efficient
    if years:
        return check_years(rows)
    return check_rows(rows)


def check_rows(rows: list):
    if len(rows[0]) >= 12:
        return INDEXES['data'].get(10)
    elif len(rows[0]) >= 9:
        return INDEXES['data'].get(7)
    elif len(rows[0]) >= 7:
        return INDEXES['data'].get(5)
    elif len(rows[0]) >= 5:
        return INDEXES['data'].get(3)
    elif len(rows[0]) >= 2:
        return INDEXES['data'].get(0)
    else:
        return None


def check_years(rows: list):
    # print('CHECKING YEARS')
    # print(rows)
    # print(len(rows))
    if len(rows) >= 11:
        return INDEXES['years'].get(10)
    elif len(rows) >= 8:
        return INDEXES['years'].get(7)
    elif len(rows) >= 6:
        return INDEXES['years'].get(5)
    elif len(rows) >= 4:
        return INDEXES['years'].get(3)
    elif len(rows) >= 1:
        return INDEXES['years'].get(0)
    else:
        return None


def click_button(locator: str):
    """Web driver waits until button is located and clicks it.

    Args:
        locator_idx (int): ID of button.
    """
    WebDriverWait(DRIVER, 10).until(
        EC.presence_of_element_located((By.XPATH, f'//button[@id="{locator}"]'))
    ).click()


def convert_curr(number: str|int|float, curr: str):
    """_summary_

    Args:
        number (str | int | float): _description_
        curr (str): _description_

    Returns:
        _type_: _description_
    """
    cr = CurrencyRates().get_rates(curr)
    conversion = cr.get('CAD')
    return number*conversion

def create_dataframes(revenue: list, eps: list, bvps: list, roe: list, roic: list, growth_yrs: list, management_years: list):
    """Stores data into dataframes.

    Args:
        revenue (list): _description_
        eps (list): _description_
        bvps (list): _description_
        roe (list): _description_
        roic (list): _description_

    Returns:
        _type_: _description_
    """
    try:
        if growth_yrs is not None:
            moat = pd.DataFrame(
                {
                    'Revenue %': revenue,
                    'EPS %': eps,
                    'BVPS %': bvps
                }, index=growth_yrs
            )
        if management_years is not None or roic is not None:
            management = pd.DataFrame(
                {
                    'ROE %': roe,
                    'ROIC %': roic
                }, index=management_years
            )
        else:
            management = pd.DataFrame(
                {
                    'ROE %': roe
                }, index=management_years
            )
        return moat, management

    except ValueError as err:
        print('ERROR in "create_dataframes" function.')
        print(err)
        return None, None

    except UnboundLocalError as err:
        return None, None


def data_available(xpath: str, section: str):
    """Searches value and returns true if found, otherwise an exeption.

    Args:
        xpath (str): XPath of element(s) to be searched.
        section (str): Section being searched.

    Returns:
        bool: True if element(s) found, otherwise False
    """
    try:
        WebDriverWait(DRIVER, 3).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        return True
    except TimeoutException:
        print(f'ERROR ~ Scraping timed out at section: {section}')
        return False


def get_currency(id):
    """_summary_

    Args:
        id (_type_): _description_

    Returns:
        _type_: _description_
    """
    curr = WebDriverWait(DRIVER, 30).until(
        EC.presence_of_element_located((By.ID, f'i{id}'))
    ).find_element(By.TAG_NAME, 'span').text.split()[0]
    return curr


def get_data(section: str, locator: str, growth_section: bool = False,
             op_eff_section: bool = False, fin_health_section: bool = False):
    """_summary_

    Args:
        section (str): Section being searched
        locator_idx (str): _description_

    Returns:
        _type_: _description_
    """
    click_button(locator)
    if growth_section:
        return get_growth_data(section)

    elif op_eff_section:
        return get_operating_and_efficiency_data(section)

    elif fin_health_section:
        return get_financial_health_data(section)

    return get_cash_flow_data(section)


def get_growth_data(section: str):
    """Searches for "Revenue %", "EPS %", and years on file in the "Growth"
    section by XPATH and returns it.

    Args:
        section (str): _description_

    Returns:
        list: Returns values in lists
    """
    if not data_available(XPATHS.get('growth'), section):
        return None
    growth_data = DRIVER.find_element(By.XPATH, XPATHS.get(section))\
        .text.splitlines()
    years = growth_data[0].split()[2:-2]
    select_years = get_years(years)[::-1]  # Reverse list

    rev_final = transform(growth_data[1:5], section=section)
    eps_final = transform(growth_data[-4:], section=section)
    return rev_final, eps_final, select_years


def get_operating_and_efficiency_data(section: str):
    """Searches for "" in "" section by XPATH and returns it.

    Args:
        section (str): _description_

    Returns:
        _type_: _description_
    """
    if not data_available(XPATHS.get('op_eff_years'), section):
        return None, None, None
    op_eff_years = DRIVER.find_element(By.XPATH, XPATHS.get('op_eff_years'))\
        .text.splitlines()[1:-2]

    select_years = get_years(op_eff_years)[::-1]  # Reverse list
    op_eff_data = DRIVER.find_element(By.XPATH, XPATHS.get('op_eff'))\
        .text.splitlines()

    roe_element = [op_eff_data[6]]
    roic_element = [op_eff_data[7]]
    roe = transform(roe_element, section=section)
    roic = transform(roic_element, section=section)
    return roe, roic, select_years

def get_financial_health_data(section: str):
    """Searches for "" in "" section by XPATH and returns it.

    Args:
        section (str): _description_

    Returns:
        _type_: _description_
    """
    if not data_available(XPATHS.get('fin_health'), section):
        return None
    fin_health = DRIVER.find_element(By.XPATH, XPATHS.get('fin_health'))\
        .text.splitlines()
    return transform(fin_health, section=section)


def get_cash_flow_data(section: str):
    """Searches for "Free Cash Flow/Share" in "Cash Flow" section by XPATH and returns it.

    Args:
        section (str): _description_

    Returns:
        _type_: _description_
    """
    if not data_available(XPATHS.get('cash_flow'), section):
        return None
    cash_flow = DRIVER.find_element(By.XPATH, XPATHS.get('cash_flow'))\
        .text.splitlines()
    return transform(cash_flow, section=section)


def get_top50():
    """Getting the indusrty of each top 50 stock.

    Returns:
        _type_: _description_
    """
    DRIVER.get('https://www.morningstar.com/stocks')
    top50 = WebDriverWait(DRIVER, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@class="mdc-carousel mdc-card-deck__carousel mdc-carousel--scrollable"]'))
    )
    top50 = top50.text.splitlines()
    return [v for v in top50 if '(' not in v]


def get_ten_cap_price(ticker: str, fcfps: np.float64, industry: str = None):
    """_summary_

    Args:
        stock (str): _description_

    Returns:
        _type_: _description_
    """
    try:
        if fcfps is None:
            return None
        if industry == 'Financial Services':
            cap_ex = 0
        else:
            cap_ex = si.get_cash_flow(ticker).loc['capitalExpenditures'][0]  # Usually negative
        shares = si.get_quote_data(ticker).get('sharesOutstanding')
        operating_cf = fcfps*shares - cap_ex

        maintenance_cap_ex = cap_ex / 2
        income_tax_exp = si.get_income_statement(ticker).loc['incomeTaxExpense'][0]
        owner_earnings = np.sum([operating_cf, maintenance_cap_ex, income_tax_exp])
        return (owner_earnings/shares* 10)

    except KeyError as err:
        try:
            if ticker in TICKER_BRIDGE:
                ticker = TICKER_BRIDGE.get(ticker)
            shares = si.get_quote_data(ticker).get('sharesOutstanding')
            cap_ex = si.get_cash_flow(ticker).loc['capitalExpenditures'][0]  # Usually negative
            operating_cf = fcfps*shares - cap_ex

            maintenance_cap_ex = cap_ex / 2
            income_tax_exp = si.get_income_statement(ticker).loc['incomeTaxExpense'][0]
            owner_earnings = np.sum([operating_cf, maintenance_cap_ex, income_tax_exp])
            return (owner_earnings/shares* 10)

        except KeyError:
            print(f'ERROR ~ {err} missing.')
            return None

    except TypeError:
        return None

def get_mos_price(stock: str, moat: pd.DataFrame):
    """_summary_

    Args:
        stock (str): _description_

    Returns:
        _type_: _description_
    """
    current_eps = si.get_quote_data(stock).get('epsCurrentYear')
    if moat is not None:
        global EPS_GR
        EPS_GR = np.nanmean(moat.iloc[-1])/100

    # Any eps growth rates higher than the limit set to default
    if EPS_GR > EPS_GR_LIM:
        EPS_GR = 0.1

    if current_eps is None:
        return None

    # EPS estimated growth rate
    eps_fv = npf.fv(EPS_GR, 10, 0, -current_eps)
    eps_fv = current_eps*(1+EPS_GR)**(10)
    pe_fv = EPS_GR*2*100
    price_fv = eps_fv*pe_fv

    intrinsic_value = npf.pv(MARR, 10, 0, -price_fv)
    return intrinsic_value/2


def get_8_year_payback_price(fcfps: float):
    if fcfps is None:
        return None
    fcf_fvs = [npf.fv(MARR, year, 0, -fcfps) for year in range(1, 11)]
    return np.sum(fcf_fvs)


def get_years(years: list):
    """Cleans year values and returns indexes of 10, 7, 5, 3, and 1 years ago.

    Args:
        years (list): Years to clean inside a list.

    Returns:
        list: Desired years in a list.
    """
    years = [pd.to_datetime(yr, format='%Y', exact=False).year for yr in years]
    idxs = check_length(years, years=True)
    if idxs is not None:
        return [years[i] for i in idxs]

    print('Function "check_years" failed to account for other test cases.')
    return None


def is_missing(s: str):
    """_summary_

    Args:
        s (str): _description_

    Returns:
        _type_: _description_
    """
    return True if NA in s else False


def is_valid(s: str):
    """
    Checks if a decimal or dash is in a string.

    Args:
        s (str): _description_

    Returns:
        _type_: _description_
    """
    return True if '.' in s or is_missing(s) else False


def get_data_averages(df: pd.DataFrame):
    """_summary_

    Args:
        moat (pd.DataFrame): _description_

    Returns:
        _type_: _description_
    """
    try:
        if df is None:
            return None
        avgs = [np.nanmean(df[col]) for col in df.columns]
        df.index.insert(-1, 'Avgs')
        df.loc['Avgs'] = avgs
        return df

    except RuntimeWarning:
        print('Warning: ROE or ROIC missing.')
        return None


def get_links():
    """Getting links of top 50 most viewed stocks from Morning Star.

    Returns:
        list: List containing top 50 stock links
    """
    search = WebDriverWait(DRIVER, 10).until(
    EC.presence_of_element_located((By.XPATH, '//*[@class="mdc-link mds-list-group__link"]'))
    ).find_elements(By.XPATH, '//*[@class="mdc-link mds-list-group__link"]')[36:68]
    links = [elem.get_attribute('href').replace('quote', 'valuation') for elem in search]
    return links


def moat_data_cleaner(data: list):
    """_summary_

    Args:
        data (list): _description_

    Returns:
        _type_: _description_
    """
    return [[elem.replace(',', '') for elem in data_list if is_valid(elem)] for data_list in data]


def page_load_catalyst():
    """Web driver clicks all buttons once located to load data.
    """
    for locator in LOCATORS[:4]:  # Key stats buttons
        WebDriverWait(DRIVER, 10).until(
            EC.presence_of_element_located((By.XPATH, f'//button[@id="{locator}"]'))
            # EC.element_to_be_clickable((By.XPATH, f'//button[@id="{locator}"]'))
        ).click()


def get_debt_to_earnings_ratio(ticker: str):
    """Gets long term debt and net income from yahoo_fin.stock_info API
    and returns the ratio.

    Args:
        ticker (str): Ticker to be searched.

    Returns:
        float: Debt to income ratio.
    """
    try:
        # Debt to net income ratio
        long_term_debt = si.get_balance_sheet(ticker).loc['longTermDebt'][0]
        earnings = si.get_income_statement(ticker).loc['netIncome'][0]
        de = long_term_debt/earnings
        return de.round(1)
    except KeyError as err:
        print(f'ERROR ~ {err} missing.')
        return None
    except IndexError as err:
        print('ERROR ~ trouble getting long term debt or net income')
        print(err)
        return None


def scrape_data(rows: list, section: str):
    """Scrapes data according to which section it belongs to.

    Args:
        rows (list): Data to be scraped
        section (str): The section being scraped.

    Returns:
        float: The value returned from a scrape format.
    """
    # try:
    if section == 'growth':
        return scrape_data_format1(rows)

    elif section == 'op_eff':
        return scrape_data_format2(rows)

    elif section == 'fin_health':
        return scrape_data_format1(rows, fin_health_section=True)
        # return scrape_data_format_3(rows)

    return scrape_data_format1(rows, cash_flow_section=True)


def scrape_data_format1(rows: list,
                        fin_health_section: bool = False,
                        cash_flow_section: bool = False):
    """_summary_

    Args:
        rows (list): _description_
        idxs (list): _description_
        section (str): _description_

    Returns:
        _type_: _description_
    """
    idxs = check_length(rows)
    if idxs is None:
        return None

    if fin_health_section:
        return [float(rows[0][i]) if not is_missing(rows[0][i]) else np.nan for i in idxs]

    elif cash_flow_section:
        return float(rows[0][-2])

    # Growth section
    rows = rows[::-1]
    rows.append(rows[-1])

    # Matches the index with the row
    locator = [*zip(idxs, rows)]
    return [float(row[i]) if not is_missing(row[i]) else np.nan for i, row in locator]


def scrape_data_format2(rows: list):
    """_summary_
    Args:
        rows (list): _description_
        idxs (list): _description_

    Returns:
        _type_: _description_
    """
    try:
        # Discard "5-Yr" column
        rows = [rows[0][:-1]]
        idxs = check_length(rows)
        if idxs is None:
            return None

        row_cleaned = [float(v) if not is_missing(v) else np.nan for v in rows[0]]
        return [np.nanmean(row_cleaned[i:-1]) if i != idxs[-1]
                else row_cleaned[-2] for i in idxs]

    except RuntimeWarning:
        print('Warning: ROE or ROIC missing.')
        return None

def scrape_data_format_3(rows: list):
    """_summary_

    Args:
        rows (list): _description_
        idxs (list): _description_

    Returns:
        _type_: _description_
    """
    idxs = check_length(rows)
    bvps_final = scrape_data_format1(rows, idxs, fin_health_section=True)
    return bvps_final


def transform(source: list, section: str):
    """Takes in a list of the data with rows split by lines.

    Args:
        source (list): List of row lists.
        idxs (list): Indexes to index row lists.
        section (str): Section

    Returns:
        _type_: _description_
    """
    value = [value.split() for value in source]
    value = moat_data_cleaner(value)
    return scrape_data(value, section)


def print_results(stock_info: str, industries: list, moat: pd.DataFrame, management: pd.DataFrame, fcfps: float):
    """Prints all relevant information for valuation.

    Args:
        stock_info (str): Gives the ticker, company name, and stock market.
        moat (pd.DataFrame): Dataframe holding Revenue %, EPS %, and BVPS %.
        management (pd.DataFrame): Dataframe holding mean ROI % and ROIC % over the years.
        fcfps (float): The latest year free cash flow per share.
    """
    ticker = stock_info.split()[0]
    try:
        industry = si.get_company_info(ticker).loc['sector']['Value']
    except TypeError:
        industry = 'NA'
        pass

    de = get_debt_to_earnings_ratio(ticker)
    moat = get_data_averages(moat)
    management = get_data_averages(management)

    # Price calculations
    ten_cap = get_ten_cap_price(ticker, fcfps, industry)
    mos = get_mos_price(ticker, moat)
    payback = get_8_year_payback_price(fcfps)

    print('-'*75)
    # Ticker, name, stock market
    print(stock_info.split('|')[0])
    print(f'Industry - {industry}')

    if moat is not None:
        moat = moat.T
    print(f'\nMoat\n{moat}\n')

    if management is not None:
        management = management.T
    print(f'Management\n{management}')

    if fcfps is not None:
        print(f'\nDebt/Earnings: {de}\n')

    print('Price Targets')
    if mos is not None:
        print(f'MOS: ${int(mos)}')

    if ten_cap is not None and payback is not None:
        print(f'Ten Cap: ${int(ten_cap)}\n8 Yr Paypack: ${int(payback)}')
    print('-'*75)


def main():
    """Runs the entire pipeline to value a stock: data collection through webscraping,
    data cleaning, data manipulation, and stock valuation.
    Top 50 most viewed stocks
    """
    try:
        start_time = time.time()
        industries = get_top50()
        links = get_links()
        for link in links:
            DRIVER.get(link)
            stock_name = DRIVER.title
            page_load_catalyst()

            # Scrape data
            rev_final, eps_final, growth_yrs = get_data('growth', LOCATORS[0], growth_section=True)
            roe_final, roic_final, op_eff_yrs = get_data('op_eff', LOCATORS[1], op_eff_section=True)
            bvps_final = get_data('fin_health', LOCATORS[2], fin_health_section=True)
            fcfps_final = get_data('cash_flow', LOCATORS[3])

            # Store data
            moat, management = create_dataframes(
                rev_final, eps_final, bvps_final,
                roe_final, roic_final, growth_yrs, op_eff_yrs
            )
            print_results(stock_name, industries, moat, management, fcfps_final)

        DRIVER.quit()
        time_taken = time.time() - start_time
        print(f'Average time taken per stock: {np.round(time_taken/len(links), 2)} seconds')
        print('-'*75)

    except KeyboardInterrupt:
        DRIVER.quit()
        sys.exit()


if __name__ == '__main__':
    main()
