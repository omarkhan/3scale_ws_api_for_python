"""Python API for ThreeScale account.

The Python API to interact with ThreeScale account. The library has
interface for following APIs.
 - authorize()
 - report()

Report GET API usage:
---------------------
    auth = ThreeScalePY.ThreeScaleAuthorize(provider_key, app_id, app_key)
    if auth.authorize():
        resp = auth.build_auth_response()
        usage_reports = resp.get_usage_reports()
        for report in usage_reports:
            print "            metric => %s" % report.get_metric()
            print "            period => %s" % report.get_period()
            print "            start => %s" % report.get_start_period()
            print "            end => %s" % report.get_end_period()
            print "            max => %s" % report.get_max_value()
            print "            current => %s" % report.get_current_value()

Authorize POST API usage:
-------------------------
    t1 = {}
    trans_usage = {}
    trans_usage['hits'] = 1
    trans_usage['max_value'] = 5
    trans_usage['timestamp'] = time.gmtime(time.time())
    t1['app_id'] = app_id OR t1['user_key']
    t1['usage'] = trans_usage

    transactions = [t1]
    resp = report.report(transactions)
"""

import urllib2
import urllib
import time
import collections

# importing ElementTree or cElementTree, whatever is available
try:
    from xml.etree.cElementTree import fromstring
except ImportError:
    try:
        from xml.etree.ElementTree import fromstring
    except ImportError:
        from elementtree.ElementTree import fromstring

__all__ = ['ThreeScale', 'ThreeScaleAuthorize', 'ThreeScaleAuthorizeResponse',
           'ThreeScaleAuthorizeResponseUsageReport', 'ThreeScaleReport']


class ThreeScale:
    """The base class to initialize the credentials and URLs"""
    def __init__(self, provider_key, app_id=None, app_key=None, user_key=None):
        """initialize the following credentials:
        - provider key
        - application id
        - application key

        The application id and key are optional. If it is omitted, the
        provider key alone is set. This is useful when the class is
        inherited by ThreeScaleReport class, for which application id
        is passed in transactions data structure and application key
        is not necessary."""
        self.domain = "su1.3scale.net"
        self.protocol = "http"

        self.app_id = app_id
        self.app_key = app_key
        self.user_key = user_key
        self.provider_key = provider_key

    def get_base_url(self):
        """return the base url for using with authorize and report
        APIs"""
        base_url = "%s://%s" % (self.protocol, self.domain)
        return base_url

    def get_auth_url(self):
        """return the url for passing authorize GET request"""
        auth_url = "%s/transactions/authorize.xml" % self.get_base_url()
        return auth_url

    def get_report_url(self):
        """return the url for passing report POST request"""
        report_url = "%s/transactions.xml" % self.get_base_url()
        return report_url


class ThreeScaleAuthorize(ThreeScale):
    """ThreeScaleAuthorize(): The derived class for ThreeScale. It is
    main class to invoke authorize GET API."""

    def get_query_string(self):
        """get the url encoded query string"""
        params = {
            'app_id': self.app_id,
            'app_key': self.app_key,
            'provider_key': self.provider_key,
        }

        return urllib.urlencode(params)

    def validate(self):
        """validate the arguments. If any of following parameters is
        missing, exit from the script.
        - application id
        - application key
        - provider key

        @throws ThreeScaleException error, if any of the credentials are
        invalid.
        """
        err = []
        if not self.app_id:
            err.append("App Id not defined")

        if not self.provider_key:
            err.append("Provider key not defined")

        if len(err):
            raise ThreeScaleException(': '.join(err))

    def authorize(self):
        """authorize() -- invoke authorize GET request.
        The authorize response is stored in a class variable.

        returns True, if authorization is successful.
        @throws ThreeScaleServerError error, if invalid response is
        received.
        @throws ThreeScaleConnectionError error, if connection can not be
        established.
        @throws ThreeScaleException error, if any other unknown error is
        occurred while receiving response for authorize GET api.
        """
        self.authorized = False
        self.auth_xml = None

        self.validate()
        auth_url = self.get_auth_url()
        query_str = self.get_query_string()

        query_url = "%s?%s" % (auth_url, query_str)

        try:
            urlobj = urllib2.urlopen(query_url)
            resp = urlobj.read()
            self.authorized = True
            self.auth_xml = resp
            return True
        except urllib2.HTTPError, err:
            if err.code == 409:  # a 409 means correct credentials but authorization failed
                self.authorized = False
                self.auth_xml = err.read()
                return False

            raise ThreeScaleServerError("Invalid response for url "
                                        "%s: %s" % (auth_url, err))
        except urllib2.URLError, err:
            raise ThreeScaleConnectionError("Connection error %s: "
                                            "%s" % (auth_url, err))
        except Exception, err:
            # handle all other exceptions
            raise ThreeScaleException("Unknown error %s: "
                                      "%s" % (auth_url, err))

    def build_auth_response(self):
        """
        Store the xml response from authorize GET api in a Python
        object, ThreeScaleAuthorizeResponse. The values in xml output
        can be retrived using the class methods.

        @returns ThreeScaleAuthorizeResponse object.
        @throws ThreeScaleException error, if xml output received from
        the server is not valid.
        """

        xml = None
        resp = ThreeScaleAuthorizeResponse()
        try:
            xml = fromstring(self.auth_xml)
        except Exception, err:
            raise ThreeScaleException("Invalid xml %s" % err)

        resp.set_plan(xml.findtext('plan'))

        if not self.authorized:
            resp.set_reason(xml.findtext('reason'))
        reports = xml.findall('usage_reports/usage_report')
        for report in reports:
            resp.add_usage_report(report)
        return resp


class ThreeScaleAuthorizeUserKey(ThreeScale):
    """ThreeScaleAuthorizeUserKey(): The derived class for ThreeScale. It is
    main class to invoke authorize GET API."""

    def get_query_string(self):
        """get the url encoded query string"""
        params = {
            'user_key': self.user_key,
            'provider_key': self.provider_key,
        }

        return urllib.urlencode(params)

    def validate(self):
        """validate the arguments. If any of following parameters is
        missing, exit from the script.
        - user key
        - provider key

        @throws ThreeScaleException error, if any of the credentials are
        invalid.
        """
        err = []
        if not self.user_key:
            err.append("User key defined")

        if not self.provider_key:
            err.append("Provider key not defined")

        if len(err):
            raise ThreeScaleException(': '.join(err))

    def authorize(self):
        """authorize() -- invoke authorize GET request.
        The authorize response is stored in a class variable.

        returns True, if authorization is successful.
        @throws ThreeScaleServerError error, if invalid response is
        received.
        @throws ThreeScaleConnectionError error, if connection can not be
        established.
        @throws ThreeScaleException error, if any other unknown error is
        occurred while receiving response for authorize GET api.
        """
        self.authorized = False
        self.auth_xml = None

        self.validate()
        auth_url = self.get_auth_url()
        query_str = self.get_query_string()

        query_url = "%s?%s" % (auth_url, query_str)
        try:
            urlobj = urllib2.urlopen(query_url)
            resp = urlobj.read()
            self.authorized = True
            self.auth_xml = resp
            return True
        except urllib2.HTTPError, err:
            if err.code == 409:  # a 409 means correct credentials but authorization failed
                self.authorized = False
                self.auth_xml = err.read()
                return False

            raise ThreeScaleServerError("Invalid response for url "
                                        "%s: %s" % (auth_url, err))
        except urllib2.URLError, err:
            raise ThreeScaleConnectionError("Connection error %s: "
                                            "%s" % (auth_url, err))
        except Exception, err:
            # handle all other exceptions
            raise ThreeScaleException("Unknown error %s: "
                                      "%s" % (auth_url, err))

    def build_auth_response(self):
        """
        Store the xml response from authorize GET api in a Python
        object, ThreeScaleAuthorizeResponse. The values in xml output
        can be retrived using the class methods.

        @returns ThreeScaleAuthorizeResponse object.
        @throws ThreeScaleException error, if xml output received from
        the server is not valid.
        """

        xml = None
        resp = ThreeScaleAuthorizeResponse()
        try:
            xml = fromstring(self.auth_xml)
        except Exception, err:
            raise ThreeScaleException("Invalid xml %s" % err)

        resp.set_plan(xml.findtext('plan'))

        if not self.authorized:
            resp.set_reason(xml.findtext('reason'))
        reports = xml.findall('usage_reports/usage_report')
        for report in reports:
            resp.add_usage_report(report)
        return resp


class ThreeScaleAuthorizeResponse():
    """The derived class for ThreeScale() class. The object constitutes
    the xml data retrived from authorize GET api."""
    def __init__(self):
        self.reason = None
        self.plan = None
        self.usage_reports = []

    def set_plan(self, plan):
        self.plan = plan

    def get_plan(self):
        return self.plan

    def set_reason(self, reason):
        self.reason = reason

    def get_reason(self):
        return self.reason

    def add_usage_report(self, xml):
        """
        Create the ThreeScaleAuthorizeResponseUsageReport object for
        each usage report.
        """
        report = ThreeScaleAuthorizeResponseUsageReport()
        report.set_metric(xml.attrib['metric'])
        report.set_period(xml.attrib['period'])
        start = xml.findtext('period_start')
        end = xml.findtext('period_end')
        report.set_interval(start, end)
        report.set_max_value(xml.findtext('max_value'))
        report.set_current_value(xml.findtext('current_value'))
        self.usage_reports.append(report)

    def get_usage_reports(self):
        """get all usage reports returned by the authorize GET api."""
        return self.usage_reports


class ThreeScaleAuthorizeResponseUsageReport():
    """Object to store all information related to the usage report."""
    def __init__(self):
        self.metric = None
        self.period = None
        self.start = None
        self.end = None
        self.max_value = None
        self.current_value = None

    def set_metric(self, metric):
        self.metric = metric

    def set_period(self, period):
        self.period = period

    def set_interval(self, start, end):
        self.start_period = start
        self.end_period = end

    def set_end_period(self, end_period):
        self.end_period = end_period

    def set_max_value(self, max_value):
        self.max_value = max_value

    def set_current_value(self, current_value):
        self.current_value = current_value

    def get_metric(self):
        return self.metric

    def get_period(self):
        return self.period

    def get_start_period(self):
        return self.start_period

    def get_end_period(self):
        return self.end_period

    def get_max_value(self):
        return self.max_value

    def get_current_value(self):
        return self.current_value


class ThreeScaleReport(ThreeScale):
    """ThreeScaleReport()
    The derived class for ThreeScale() base class, for making report
    POST request.
    """

    def build_post_data(self, transactions):
        return "provider_key=%s%s" % (self.provider_key, self.encode_transactions(transactions))

    def encode_transactions(self, transactions):
        """
        @throws ThreeScaleException error, if transaction is invalid.
        """
        encoded = ''
        i = 0

        if not isinstance(transactions, collections.Iterable):
            raise ThreeScaleException("Invalid transaction type")

        for trans in transactions:
            prefix = "&transactions[%d]" % (i)
            encoded += self.encode_recursive(prefix, trans)
            i += 1

        return encoded

    def encode_recursive(self, prefix, trans):
        """encode every value in transactions
        @throws ThreeScaleException error, if the timestamp specified in
        transaction is invalid.
        """
        new_value = ""
        for key in trans.keys():
            if key == 'usage':  # usage is list
                new_prefix = "%s[usage]" % (prefix,)
                new_value += self.encode_recursive(new_prefix, trans[key])
            elif key == 'timestamp':  # specially encode the timestamp
                ts = trans[key]
                try:
                    new_value += "%s[%s]=%s" % (prefix, key, urllib2.quote(str(time.strftime('%Y-%m-%d %H:%M:%S %z', ts))))
                except:
                    raise ThreeScaleException("Invalid timestamp "
                                              "'%s' specified in "
                                              "transaction" % ts)
            else:
                new_value += ("%s[%s]=%s" % (prefix, key, urllib2.quote(str(trans[key]))))

        return new_value

    def report(self, transactions):
        """send the report POST request.

        @returns True, if request is sent successfully.
        @throws ThreeScaleServerError error, if invalid response is
        received.
        @throws ThreeScaleConnectionError error, if connection can not be
        established.
        @throws ThreeScaleException error, if any other unknown error is
        occurred while receiving response for report POST api.
        """

        report_url = self.get_report_url()
        data = self.build_post_data(transactions)

        try:
            req = urllib2.Request(report_url, data)
            urllib2.urlopen(req)
            return True
        except urllib2.HTTPError, err:
            raise ThreeScaleServerError("Invalid response for url "
                                        "%s: %s" % (report_url, err))
            return False
        except urllib2.URLError, err:
            raise ThreeScaleConnectionError("Connection error %s: "
                                            "%s" % (report_url, err))
            return False
        except Exception, err:
            # handle all other exceptions
            raise ThreeScaleException("Unknown error %s: "
                                      "%s" % (report_url, err))
            return False


class ThreeScaleException(Exception):
    """main exception class. raise this exception for all other errors"""
    pass


class ThreeScaleServerError(ThreeScaleException):
    """raise exception if there are any exception during server
    interaction"""
    pass


class ThreeScaleConnectionError(ThreeScaleException):
    """raise exception if server connection can not be establised"""
    pass
