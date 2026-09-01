import re
for fname in [
    'dashboard/templates/dashboard/accounts.html',
    'dashboard/templates/dashboard/profile.html',
]:
    content = open(fname, 'r', encoding='utf-8').read()
    content = re.sub(r"fetch\(`/accounts/", "fetch(`/dashboard/accounts/", content)
    content = re.sub(r"fetch\(`/resumes/", "fetch(`/dashboard/resumes/", content)
    content = content.replace("href='/accounts/'", "href='/dashboard/accounts/'")
    content = content.replace("href=\"/accounts/\"", "href=\"/dashboard/accounts/\"")
    content = content.replace("action=\"/accounts/", "action=\"/dashboard/accounts/")
    content = content.replace("'/accounts/", "'/dashboard/accounts/")
    content = content.replace('\"/accounts/', '\"/dashboard/accounts/')
    content = content.replace("fetch('/resumes/", "fetch('/dashboard/resumes/")
    open(fname, 'w', encoding='utf-8').write(content)
    print(f'Fixed: {fname}')
