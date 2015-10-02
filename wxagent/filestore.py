import hashlib

from PyQt5.QtCore import QByteArray

import qiniu


# @param data bytes
def md5_file(data):
    h = hashlib.md5()
    h.update(data)
    return h.hexdigest()


# @param data bytes | QByteArray
def upload_file(data):
    if type(data) == QByteArray:
        data = data.data()
    from .secfg import qiniu_acckey, qiniu_seckey, qiniu_bucket_name
    access_key = qiniu_acckey
    secret_key = qiniu_seckey
    bucket_name = qiniu_bucket_name

    q = qiniu.Auth(access_key, secret_key)
    key = 'helloqt.png'
    key = md5_file(data)
    # data = 'hello qiniu!'
    # data = load_from_file(PATH)
    token = q.upload_token(bucket_name)
    ret, info = qiniu.put_data(token, key, data)
    if ret is not None:
        print('upload file All is OK', ret)
    else:
        print(ret, '=====', info)  # error message in info

    url = 'http://7xn2rb.com1.z0.glb.clouddn.com/%s' % key
    return url
