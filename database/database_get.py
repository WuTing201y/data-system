import mysql.connector

link = mysql.connector.connect(
    host = 'localhost',
    port = 3306,
    user = 'root',
    password = 'zaxscdvf',
    database = 'database001'
)

base = link.cursor()

def by_year(keyword): 
    conment = "SELECT * FROM `houses` WHERE YEAR(`trade_date`) = " + str(keyword)
    return output(conment)

def by_month(keyword):
    conment = "SELECT * FROM `houses` WHERE MONTH(`trade_date`) = " + str(keyword)
    return output(conment)

def by_year_month(year,month):
    conment = "SELECT * FROM `houses` WHERE YEAR(`trade_date`) = " + str(year) + " AND MONTH(`trade_date`) = " + str(month)
    return output(conment)

def by_district(keyword):
    conment = "SELECT * FROM `houses` WHERE `district` = '" + str(keyword) + "'"
    return output(conment)

def by_district_year(keyword,year):
    conment = "SELECT * FROM `houses` WHERE `district` = '" + str(keyword) + "' AND YEAR(`trade_date`) = " + str(year)
    return output(conment)

def by_district_year_month(keyword,year,month):
    conment = "SELECT * FROM `houses` WHERE `district` = '" + str(keyword) + "' AND YEAR(`trade_date`) = " + str(year) + " AND MONTH(`trade_date`) = " + str(month)
    return output(conment)

def by_price(lower,upper):
    conment = "SELECT * FROM `houses` WHERE `price_total` between " + str(lower) + " AND " + str(upper)
    return output(conment)

def by_district_price(keyword,lower,upper):
    conment = "SELECT * FROM `houses` WHERE `price_total` between " + str(lower) + " AND " + str(upper) + " AND `district` = '" + str(keyword) + "'"
    return output(conment)

def by_district_price_time(keyword,lower,upper,year,month):
    conment = "SELECT * FROM `houses` WHERE `price_total` between " + str(lower) + " AND " + str(upper) + " AND `district` = '" + str(keyword) + "' AND YEAR(`trade_date`) = " + str(year) + " AND MONTH(`trade_date`) = " + str(month)
    return output(conment)

def by_area(lower,upper):
    conment = "SELECT * FROM `houses` WHERE `area_ping` between " + str(lower) + " AND " + str(upper)
    return output(conment)

def by_district_area(keyword,lower,upper):
    conment = "SELECT * FROM `houses` WHERE `area_ping` between " + str(lower) + " AND " + str(upper) + " AND `district` = '" + str(keyword) + "'"
    return output(conment)

def by_district_area_price(keyword,a_lower,a_upper,p_lower,p_upper):
    conment = "SELECT * FROM `houses` WHERE `area_ping` between " + str(a_lower) + " AND " + str(a_upper) + " AND `district` = '" + str(keyword) + "' AND `price_total` between " + str(p_lower) + " AND " + str(p_upper)
    return output(conment)

def by_age(lower,upper):
    conment = "SELECT * FROM `houses` WHERE `age_years` between " + str(lower) + " AND " + str(upper)
    return output(conment)

def by_district_age(keyword,lower,upper):
    conment = "SELECT * FROM `houses` WHERE `age_years` between " + str(lower) + " AND " + str(upper) + " AND `district` = '" + str(keyword) + "'"
    return output(conment)

def search(district,price,age,area):
    conment = "SELECT * FROM `houses` WHERE `price_total` between " + str(price[0]) + " AND " + str(price[1]) + " AND `district` = '" + str(district) + "' AND `age_years` between " + str(age[0]) + " AND " + str(age[1]) + " AND `area_ping` between " + str(area[0]) + " AND " + str(area[1])
    return output(conment)

def search_bytime(district,price,age,area,time):
    conment = "SELECT * FROM `houses` WHERE `price_total` between " + str(price[0]) + " AND " + str(price[1]) + " AND `district` = '" + str(district) + "' AND YEAR(`trade_date`) = " + str(time[0]) + " AND MONTH(`trade_date`) = " + str(time[1])+ " AND `age_years` between " + str(age[0]) + " AND " + str(age[1]) + " AND `area_ping` between " + str(area[0]) + " AND " + str(area[1])
    return output(conment)

def output(conment):
    base.execute(conment)
    return base

#for row in by_district_age('鶯歌區',1,12).fetchall() :
#    print(row)