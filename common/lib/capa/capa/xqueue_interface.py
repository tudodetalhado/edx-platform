#
#  LMS Interface to external queueing system (xqueue)
#
import hashlib
import json
import requests
import time

# TODO: Collection of parameters to be hooked into rest of edX system
XQUEUE_LMS_AUTH = { 'username': 'LMS',
                    'password': 'PaloAltoCA' }
XQUEUE_URL = 'http://xqueue.edx.org'

def make_hashkey(seed=None):
    '''
    Generate a string key by hashing 
    '''
    h = hashlib.md5()
    if seed is not None:
        h.update(str(seed))
    h.update(str(time.time()))
    return h.hexdigest()


def make_xheader(lms_callback_url, lms_key, queue_name):
    '''
    Generate header for delivery and reply of queue request.

    Xqueue header is a JSON-serialized dict:
        { 'lms_callback_url': url to which xqueue will return the request (string),
          'lms_key': secret key used by LMS to protect its state (string), 
          'queue_name': designate a specific queue within xqueue server, e.g. 'MITx-6.00x' (string)
        }
    '''
    return json.dumps({ 'lms_callback_url': lms_callback_url,
                        'lms_key': lms_key,
                        'queue_name': queue_name })


def send_to_queue(header, body, file_to_upload=None, xqueue_url=XQUEUE_URL):
    '''
    Submit a request to xqueue.
    
    header: JSON-serialized dict in the format described in 'xqueue_interface.make_xheader'

    body: Serialized data for the receipient behind the queueing service. The operation of
            xqueue is agnostic to the contents of 'body'

    file_to_upload: File object to be uploaded to xqueue along with queue request

    Returns an 'error' flag indicating error in xqueue transaction
    '''

    # First, we login with our credentials
    #------------------------------------------------------------
    s = requests.session()
    try:
        r = s.post(xqueue_url+'/xqueue/login/', data={ 'username': XQUEUE_LMS_AUTH['username'],
                                                       'password': XQUEUE_LMS_AUTH['password'] })
    except Exception as err:
        msg = 'Error in xqueue_interface.send_to_queue %s: Cannot connect to server url=%s' % (err, xqueue_url)
        raise Exception(msg)

    # Xqueue responses are JSON-serialized dicts
    (return_code, msg) = parse_xreply(r.text)
    if return_code: # Nonzero return code from xqueue indicates error
        print '  Error in queue_interface.send_to_queue: %s' % msg
        return 1 # Error

    # Next, we can make a queueing request
    #------------------------------------------------------------
    payload = {'xqueue_header': header,
               'xqueue_body'  : body}

    files = None
    if file_to_upload is not None:
        files = { file_to_upload.name: file_to_upload }

    try:
        r = s.post(xqueue_url+'/xqueue/submit/', data=payload, files=files)
    except Exception as err:
        msg = 'Error in xqueue_interface.send_to_queue %s: Cannot connect to server url=%s' % (err, xqueue_url)
        raise Exception(msg)

    (return_code, msg) = parse_xreply(r.text)
    if return_code:
        print '  Error in queue_interface.send_to_queue: %s' % msg

    return return_code

def parse_xreply(xreply):
    '''
    Parse the reply from xqueue. Messages are JSON-serialized dict:
        { 'return_code': 0 (success), 1 (fail),
          'content': Message from xqueue (string)
        }
    '''
    xreply = json.loads(xreply)
    return_code = xreply['return_code']
    content = xreply['content']
    return (return_code, content)
