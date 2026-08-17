from agents.tag_policy import normalize_tags, normalize_posts_tags

assert normalize_tags(['AI비전검사','머신 비전','아진네트웍스']) == ['딥러닝비전','머신비전']
assert normalize_tags(['AGV','AMR','물류로봇','WMS','컨베이어','기타']) == ['AGV','AMR','WMS','컨베이어']
assert len(normalize_tags(['PLC','HMI','SCADA','MES','OPC-UA','EtherCAT'])) == 5
posts=[{'title':'3D 비전검사와 PLC 연동','tags':['3d 비전','PLC제어'],'category':'딥러닝비전','content':'머신 비전 검사'}]
normalize_posts_tags(posts)
assert posts[0]['tags'][0] == '3D비전'
assert 'PLC' in posts[0]['tags']
assert '머신비전' in posts[0]['tags']
print('TAG POLICY TESTS: PASS')
