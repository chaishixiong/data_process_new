import re, os, redis
import socket, random
from smt_spider.Bloomfilter import BloomFilter
from lxml import etree
from tqdm import tqdm
import asyncio
import time
from pyppeteer.launcher import launch  # 控制模拟浏览器用
from retrying import retry  # 设置重试次数用的
import random,numpy
from pyppeteer.errors import TimeoutError


def get_ip():
    addrs = socket.getaddrinfo(socket.gethostname(), "")
    match = re.search("'192.168.\d+.(\d+)'", str(addrs))
    ip_num = "000"
    if match:
        ip_num = match.group(1)
    return ip_num


def connect():
    name = "kdlj"
    username = '{}'.format('')
    password = '{}'.format('')
    cmd_str = "rasdial %s %s %s" % (name, username, password)
    res = os.system(cmd_str)
    if res == 0:
        print("连接成功")
    else:
        print(res)


def disconnect():
    name = "kdlj"
    cmdstr = "rasdial %s /disconnect" % name
    os.system(cmdstr)
    print('断开成功')


def huan_ip():
    # 断开网络
    disconnect()
    # 开始拨号
    connect()

class smt_pz_info(object):
    def __init__(self, zhanghao, ADSL_name, ADSL_pwd):
        self.r = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True,password="nriat.123456")
        self.bf = BloomFilter('SmtPzInfoSpider')
        self.cache_queue = 'smt_pzinfo_cache_queque'
        self.main_queue = "smt_pzinfo"
        self.ADSL_name = ADSL_name
        self.ADSL_pwd = ADSL_pwd
        self.zhanghao_list = zhanghao
        self.write()
        self.page = None
        self.browser = None
        # self.huan_ip()

    # 检测当前程序进程pid,并存入文本中
    def write(self):
        pid = os.getpid()
        with open('pid.txt', 'w', encoding='utf-8') as f:
            f.write(str(pid))

    # ----------------------自动拨号更换IP-----------------------------

    def run(self):
        # 领取并执行采集任务
        print('--------------------------开始采集--------------------------')
        while True:
            task_list = []
            check_cache_queue = self.r.scard(self.cache_queue)
            if check_cache_queue > 0:
                # 缓存队列不为空，返回缓存队列所有数据
                using_data = self.r.smembers(self.cache_queue)
                print('-----清理缓存队列-----')
                for i in tqdm(using_data):
                    if self.bf.isContains(i):
                        # 该参数已采集到数据则从缓存队列删除
                        self.r.srem(self.cache_queue, i)
                    else:
                        # 该参数未采集到数据则添加进主队列，然后从缓存队列删除
                        self.r.sadd(self.main_queue, i)
                        self.r.srem(self.cache_queue, i)
            if self.r.exists(self.main_queue):
                self.run_task()
                # 判断列表是否为空，如果为空，则说明没有任务生成
            else:
                print('------未找到任务队列--------')
            time.sleep(60)

    def run_task(self):
        while True:
            loop = asyncio.get_event_loop()  # 协程，开启个无限循环的程序流程，把一些函数注册到事件循环上。当满足事件发生的时候，调用相应的协程函数。
            loop.run_until_complete(self.main())
            time.sleep(10)

    def Authens(self):
        proxyUser = 'FD091B0A'
        proxyPass = '41D2415C2395'
        # server = 'tunnel5.qg.net:15989'
        authen = {'username': proxyUser, 'password': proxyPass}
        return authen


    async def main(self):  # 定义main协程函数，
        # huan_ip()
        # 以下使用await 可以针对耗时的操作进行挂起
        self.browser = await launch({'headless': False, 'args': ['--no-sandbox'], 'dumpio':True,"userDataDir":r"D:\spider_data\taobao_pyppeteer"})  # 启动pyppeteer 属于内存中实现交互的模拟器 process.stdout 和 process.stderr 对象，默认是 False。
        browser_context = await self.browser.createIncognitoBrowserContext()
        self.page = await browser_context.newPage()  # 启动个新的浏览器页面
        await self.page.setUserAgent(
            'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36')
        await self.login()
        await self.goto_page()
        await self.page.close()
        await self.browser.close()
        # await get_cookie(page)
        # time.sleep(100)

        # try:
        #     global error  # 检测是否是账号密码错误
        #     print("error_1:", error)
        #     error = await page.Jeval('.error', 'node => node.textContent')
        #     print("error_2:", error)
        # except Exception as e:
        #     error = None
        # finally:
        #     if error:
        #         print('确保账户安全重新入输入')
        #         # 程序退出。
        #         loop.close()
        #     else:
        #         print(page.url)

    async def goto_page_txt(self):#测试废弃，从文本得到shopid

        num = 0
        with open(r"C:\Users\Administrator\Desktop\{smt_shopid}[shopid].txt", "r", encoding="utf-8") as f:
            for i in f:
                print(num)
                num += 1
                i = i.strip()
                await self.get_page(i)

    async def cookie_to_dic(self, cookie):
        cookies_list = []
        for item in cookie.split('; '):
            cooie_dict = dict()
            item_list = item.split('=')
            cooie_dict['name'] = item_list[0]
            cooie_dict['value'] = item_list[1]
            cooie_dict['domain'] = '.aliexpress.com'
            cookies_list.append(cooie_dict)
        return cookies_list
        # return {item.split('=')[0]: item.split('=')[1] for item in cookie.split('; ')}

    async def login(self,):
        smt_name = self.zhanghao_list[random.randint(0,2)]
        smt_pw = 'a123456789'
        url = 'https://login.aliexpress.com/'

        await self.page.goto(url)  # 访问登录页面
        # 替换淘宝在检测浏览时采集的一些参数。
        # 就是在浏览器运行的时候，始终让window.navigator.webdriver=false
        # navigator是windiw对象的一个属性，同时修改plugins，languages，navigator 且让
        cookie = await self.page.cookies()
        await self.page.evaluate(
            '''() =>{ Object.defineProperties(navigator,{ webdriver:{ get: () => false } }) }''')  # 以下为插入中间js，将淘宝会为了检测浏览器而调用的js修改其结果。
        # await self.page.evaluate('''() =>{ window.navigator.chrome = { runtime: {},  }; }''')
        # await self.page.evaluate(
        #     '''() =>{ Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] }); }''')
        # await self.page.evaluate(
        #     '''() =>{ Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5,6], }); }''')

        # 使用type选定页面元素，并修改其数值，用于输入账号密码，修改的速度仿人类操作，因为有个输入速度的检测机制
        # 因为 pyppeteer 框架需要转换为js操作，而js和python的类型定义不同，所以写法与参数要用字典，类型导入
        # await page.waitFor('#alibaba-login-box')
        # a = page.frames[1]

        await self.page.type('#fm-login-id', smt_name, {'delay': self.input_time_random() - 50})
        await self.page.type('#fm-login-password', smt_pw, {'delay': self.input_time_random()})

        # await page.screenshot({'path': './headless-example-result.png'})    # 截图测试

        # 检测页面是否有滑块。原理是检测页面元素。
        # slider1 = await page.Jeval('#nc_1_n1z', 'node => node.style')  # 是否有滑块
        slider = await self.page.querySelector('#nc_1_n1z')
        # slider = 0
        #
        if slider:
            print('当前页面出现滑块')
            # await page.screenshot({'path': './headless-login-slide.png'}) # 截图测试
            statue = await self.mouse_slide()  # js拉动滑块过去。
            if statue:
                # await page.keyboard.press('Enter')  # 确保内容输入完毕，少数页面会自动完成按钮点击
                print("print enter", statue)
                await self.page.evaluate(
                    '''document.querySelector(".fm-button").click()''')  # 如果无法通过回车键完成点击，就调用js模拟点击登录按钮。
                await self.page.waitForNavigation()

                # time.sleep(2)
                # cookies_list = await page.cookies()
                # print(cookies_list)
                # await get_cookie(page)  # 导出cookie 完成登陆后就可以拿着cookie玩各种各样的事情了。
        else:
            await self.page.keyboard.press('Enter')
            print("print enter")
            time.sleep(8)
            # iframe = await self.page.content()
            # await self.page.reload()
            # await self.page.waitFor(1000)
            # slider = await self.page.querySelector('#nc_1_n1z')
            iframe = await self.page.cookies()
            # addd = iframe.content()
            # await self.mouse_slide()
            # await self.page.evaluate(
            #     '''document.querySelector("comet-btn comet-btn-primary comet-btn-large comet-btn-block login-submit").click()''')
            time.sleep(5)
            try:
                await self.page.waitForNavigation()
            except TimeoutError as te:
                print(te)

    async def goto_page(self):
        ip = get_ip()
        file = open(r'C:/Users/Administrator/Desktop/{{速卖通牌照信息_{}}}[店铺ID,公司名称,增值税税号,营业执照注册号,地址,联系人,业务范围,创建时间,登记机关].txt'.format(ip),'a', encoding='utf-8')
        error_num = 0
        while True:
            # ---------------------------------------------------------------------
            shop_id = self.r.spop(str(self.main_queue))
            # 将获取的数据存储到另外一个集合中，防止程序中途停止导致数据丢失
            if shop_id == None:
                print('当前采集任务完成')
                break
            else:
                self.r.sadd(self.cache_queue, shop_id)
                # 判断是不是没有数据的店铺
                if self.bf.isContains(shop_id):
                    # 采集完成，从缓存队列中删除
                    self.r.srem(self.cache_queue, shop_id)
                else:
                    try:
                        statue,data = await self.get_page(shop_id)
                        await asyncio.sleep(1)
                        if statue:
                            str_data = ",".join([i for i in data.values()])+"\n"
                            file.write(str_data)#保存文本
                            file.flush()
                            self.bf.insert(shop_id)
                            self.r.srem(self.cache_queue, shop_id)
                            error_num = 0
                        else:
                            error_num += 1
                            self.r.sadd(self.main_queue,shop_id)
                            self.r.srem(self.cache_queue, shop_id)
                            if error_num >= 5:
                                break
                    except Exception as e:
                        print(e)

    async def get_page(self, id):
        url = "https://sellerjoin.aliexpress.com/credential/showcredential.htm?storeNum={}".format(id)
        # url = 'http://pv.sohu.com/cityjson'
        try:
            # await self.page.authenticate(self.Authens())
            cookies = [{'name': 'ali_apache_id', 'value': '33.8.114.84.1675144615977.338590.5', 'domain': '.aliexpress.com', 'path': '/', 'expires': 3626384462.940168, 'size': 47, 'httpOnly': False, 'secure': False, 'session': False}, {'name': 'l', 'value': 'fBP79fknTWjySULtBOfaFurza77OSIRYYuPzaNbMi9fP9gCB5veRW6JTP0Y6C3GcFstDR30LMK_eBeYBq7VonxvTN0_vBdHmndLHR35..', 'domain': '.aliexpress.com', 'path': '/', 'expires': 1690696618, 'size': 106, 'httpOnly': False, 'secure': False, 'session': False}, {'name': 'aep_usuc_f', 'value': 'site=glo&b_locale=en_US', 'domain': '.aliexpress.com', 'path': '/', 'expires': 3822628264.940335, 'size': 33, 'httpOnly': False, 'secure': False, 'session': False}, {'name': 'xman_us_f', 'value': 'x_l=1&x_locale=en_US&x_c_chg=1&acs_rt=447d66de26c947ebbd27b3e644f098ab', 'domain': '.aliexpress.com', 'path': '/', 'expires': 3822628265.281738, 'size': 79, 'httpOnly': False, 'secure': False, 'session': False}, {'name': 'intl_locale', 'value': 'en_US', 'domain': '.aliexpress.com', 'path': '/', 'expires': -1, 'size': 16, 'httpOnly': False, 'secure': False, 'session': True}, {'name': 'acs_usuc_t', 'value': 'acs_rt=447d66de26c947ebbd27b3e644f098ab&x_csrf=f9igg834ci75', 'domain': '.aliexpress.com', 'path': '/', 'expires': -1, 'size': 69, 'httpOnly': False, 'secure': False, 'session': True}, {'name': 'intl_common_forever', 'value': 'RSTkJHtFWY3sj6mJ2ZCKvHNZ9eXzfPqXuwToga7uNbBlbp6NgA9SNA==', 'domain': '.aliexpress.com', 'path': '/', 'expires': 3822628264.940377, 'size': 75, 'httpOnly': True, 'secure': False, 'session': False}, {'name': 'xman_t', 'value': '7ZYrfaBxSElJUZ4hJ+eYyuNOuv2z8ufBYhdaU3NhTWI4piBPOMQlz4Bl/HYLoTx1', 'domain': '.aliexpress.com', 'path': '/', 'expires': 1682920617.940349, 'size': 70, 'httpOnly': True, 'secure': False, 'session': False}, {'name': 'ali_apache_track', 'value': '', 'domain': '.aliexpress.com', 'path': '/', 'expires': 3822628265.281702, 'size': 16, 'httpOnly': False, 'secure': False, 'session': False}, {'name': 'ali_apache_tracktmp', 'value': '', 'domain': '.aliexpress.com', 'path': '/', 'expires': -1, 'size': 19, 'httpOnly': False, 'secure': False, 'session': True}, {'name': 'xman_f', 'value': '+ukBwDcdoGq8LcFViE/Uo4lJTsTX0S7tcpE/htaB+hRzKTN2EbwmdgOicZMoPphpQcp9V7hX+FLJiqsGXiYjvDYw/0sJzVIlBHhE+SbTl7Ycm7BnZdjzhg==', 'domain': '.aliexpress.com', 'path': '/', 'expires': 3822628264.940395, 'size': 126, 'httpOnly': True, 'secure': False, 'session': False}, {'name': 'isg', 'value': 'BI-P0jPTMF7AkjSiPGZIAStmHiOZtOPWPHRZV6GcK_4FcK9yqYRzJo3icqFOE7tO', 'domain': '.aliexpress.com', 'path': '/', 'expires': 1690696618, 'size': 67, 'httpOnly': False, 'secure': False, 'session': False}, {'name': '_bl_uid', 'value': 'ntlO7d06jabt3ju0jr1Cydt68UL4', 'domain': 'login.aliexpress.com', 'path': '/', 'expires': 1690696618.494886, 'size': 35, 'httpOnly': False, 'secure': False, 'session': False}, {'name': 'tfstk', 'value': 'c36RBvA5Nr4kLEzH3LFmTb7O-DUGwPNJk0txpOWPgg-cfE1mhOXwf7PWuyk8D', 'domain': '.aliexpress.com', 'path': '/', 'expires': 1690696618, 'size': 66, 'httpOnly': False, 'secure': False, 'session': False}, {'name': 'xlly_s', 'value': '1', 'domain': '.aliexpress.com', 'path': '/', 'expires': 1675231018, 'size': 7, 'httpOnly': False, 'secure': True, 'session': False}, {'name': 'cna', 'value': 'qZtfHBEDpWMCAbedTFJmFm8I', 'domain': '.aliexpress.com', 'path': '/', 'expires': 2305864618, 'size': 27, 'httpOnly': False, 'secure': False, 'session': False}]
            # await self.page.setCookie(*cookies)
            await self.page.goto(url)
            time.sleep(5)
            await self.page.evaluate(
                '''() =>{ Object.defineProperties(navigator,{ webdriver:{ get: () => false } }) }''')  # 以下为插入中间js，将淘宝会为了检测浏览器而调用的js修改其结果。
            # await self.page.waitFor(1)
            # await self.page.evaluate('''() =>{ window.navigator.chrome = { runtime: {},  }; }''')
            # await self.page.evaluate(
            #     '''() =>{ Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] }); }''')
            # await self.page.evaluate(
            #     '''() =>{ Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5,6], }); }''')
        except Exception as e:
            print(e)
        cookies_list = await self.page.cookies()
        # await page.waitForNavigation()
        # data_html = self.page.content()
        # if '请拖动下方滑块完成验证' in data_html:
        #     pass
        await asyncio.sleep(1)
        statue = await self.mouse_slide()
        # slider = await self.page.querySelector('#nc_1_n1z')
        # await self.page.waitFor(5)
        # if slider:
        #     statue = await self.mouse_slide()
        shopid = id
        if statue:
            company_dict = {"shopid": shopid,
                            "Company name：": "",
                            "VAT number：": "",
                            "registration number：": "",
                            "Address：": "",
                            "Corporate：": "",
                            "Scope：": "",
                            "Established：": "",
                            "authority：": ""}
            content = await self.page.content()
            if 'system error!' in content:
                # await self.page.reload()
                # statue = await self.mouse_slide()
                print('sssssssssssssssssssssssssssssss')
            elif "No Data" in content:
                return 1,company_dict
            elif "information" in content and "something's wrong" not in content:
                text_elements = await self.page.xpath('//div[@id="container"]/div')
                for item in text_elements:
                    title_str = await (await item.getProperty('textContent')).jsonValue()
                    for text_i in company_dict:
                        if text_i in title_str:
                            data = title_str.split(text_i)[-1].strip()
                            data = data.replace(",", "，")
                            data = data.replace("\n", "")
                            company_dict[text_i] = data
                return 1,company_dict
            else:
                return 0,{}
        else:
            return 0, {}

    # 获取登录后cookie
    async def get_cookie(self,page):
        # res = await page.content()
        cookies_list = await page.cookies()
        cookies = ''
        for cookie in cookies_list:
            str_cookie = '{0}={1};'
            str_cookie = str_cookie.format(cookie.get('name'), cookie.get('value'))
            cookies += str_cookie
        print(cookies)
        return cookies

    def get_path(self,distance):
        result = []
        current = 0
        mid = distance * 4 / 5
        t = 0.2
        v = 0
        while current < (distance - 10):
            if current < mid:
                a = 2
            else:
                a = -3
            v0 = v
            v = v0 + a * t
            s = v0 * t + 0.5 * a * t * t
            current += s
            result.append(round(s))
        return result

    def random_linspace(self,num, length):
        '''辅助函数
        传入要分成的几段 -> num ；长度 -> length, 生成一个递增的、随机的、不严格等差数列
        '''
        # 数列的起始值 、 结束值。 这里以平均值的 0.5 作为起始值，平均值的 1.5倍作为结束值。
        start, end = 0.5 * (length / num), 1.5 * (length / num)
        # 借助三方库生成一个标准的等差数列，主要是得出标准等差 space
        origin_list = numpy.linspace(start, end, num)
        space = origin_list[2] - origin_list[1]
        # 在标准等差的基础上，设置上下浮动的大小，（上下浮动10%）
        min_random, max_random = -(space / 10), space / 10
        result = []
        # 等差数列的初始值不变，就是我们设置的start
        value = start
        # 将等差数列添加到 list
        result.append(value)
        # 初始值已经添加，循环的次数 减一
        for i in range(num - 1):
            # 浮动的等差值 space
            random_space = space + random.uniform(min_random, max_random)
            value += random_space
            result.append(value)
        return result

    def slide_list(self,total_length):
        '''等差数列生成器，根据传入的长度，生成一个随机的，先递增后递减，不严格的等差数列'''
        # 具体分成几段是随机的
        total_num = random.randint(10, 15)
        # 中间的拐点是随机的
        mid = total_num - random.randint(3, 5)
        # 第一段、第二段的分段数
        first_num, second_num = mid, total_num - mid
        # 第一段、第二段的长度，根据总长度，按比例分成
        first_length, second_length = total_length * (first_num / total_num), total_length * (second_num / total_num)
        # 调用上面的辅助函数，生成两个随机等差数列
        first_result = self.random_linspace(first_num, first_length)
        second_result = self.random_linspace(second_num, second_length)
        # 第二段等差数列进行逆序排序
        slide_result = first_result + second_result[::-1]
        # 由于随机性，判断一下总长度是否满足，不满足的再补上一段
        if sum(slide_result) < total_length:
            slide_result.append(total_length - sum(slide_result))
        return slide_result

    def retry_if_result_none(self,result):
        return result is None

    async def mouse_slide(self):
        # await asyncio.sleep(1)
        # try:
        #     # 鼠标移动到滑块，按下，滑动到头（然后延时处理），松开按键
        #     await self.page.hover('#nc_1_n1z')  # 不同场景的验证码模块能名字不同。
        #     await self.page.mouse.down()
        #     # for x in get_path(5)
        #     a = self.page.mouse._x
        #     for i in self.slide_list(500):
        #         a += i
        #         await self.page.mouse.move(a, 0, )
        #     await self.page.mouse.up()
        # except Exception as e:
        #     print(e, ':验证失败')
        #     return None
        # else:
        #     await asyncio.sleep(1)
        #     return 1
        await asyncio.sleep(1)
        try:
            # 鼠标移动到滑块，按下，滑动到头（然后延时处理），松开按键
            el = await self.page.querySelector('div[class="scale_text slidetounlock"]')
            box = await el.boundingBox()
            await self.page.hover('#nc_1_n1z')  # 不同场景的验证码模块能名字不同。
            await self.page.mouse.down()
            # for x in get_path(5)
            number = random.randint(3500, 5000)
            await self.page.mouse.move(box['x'] + number, box['y'] + 10, {'delay': 5000, 'steps': 56})
            # await self.page.mouse.move(box['x'] + 700, box['y'] + 10, {'delay': 5000, 'steps': 56})
        except Exception as e:
            print(e, ':验证失败1')
            return None
        else:
            await asyncio.sleep(1)
            return 1

    async def bx_mouse_slide(self):
        await asyncio.sleep(1)
        try:
            # 鼠标移动到滑块，按下，滑动到头（然后延时处理），松开按键
            # await self.page.hover('#nc_1_n1z')  # 不同场景的验证码模块能名字不同。
            # await self.page.mouse.down()
            # 获取滑块的尺寸
            el = await self.page.querySelector('div[class="scale_text slidetounlock"]')
            box = await el.boundingBox()
            # 鼠标悬浮在块上
            await self.page.hover('#nc_1_n1z')
            # 按下鼠标
            await self.page.mouse.down()
            # 移动鼠标, 数字调试几次就知道了, 延迟设大点
            await self.page.mouse.move(box['x'] + 700, box['y'] + 10, {'delay': 5000, 'steps': 56})
            # 松开鼠标
            await self.page.mouse.up()
        except Exception as e:
            print(e, ':验证失败')
            return None
        else:
            await asyncio.sleep(1)
            return 1

    def input_time_random(self):
        return random.randint(100, 151)


if __name__=="__main__":
    zhanghao = []
    with open('D:\data_process\smt_spider\任务文件\账号列表\账号56-1.txt', 'r', encoding='utf-8') as f:
        for i in f:
            zhanghao.append(i.strip())
    # python配置文件路径
    ip = get_ip()
    if ip in [59,56,98,99]:
        ADSL_name = "057762355592"
        ADSL_pwd = "928858"
    else:
        ADSL_name = "057762355594"
        ADSL_pwd = "045805"
    get = smt_pz_info(zhanghao, ADSL_name, ADSL_pwd)
    get.run()



