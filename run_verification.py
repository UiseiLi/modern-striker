from pathlib import Path
import concurrent.futures,json,subprocess,sys
root=Path(__file__).parent
v=root/'verification'
exe=root/'现代突击者_正式版.exe'
cases=[]
for mode in ['assets','core','qol','pool','collision','banner','loops']:
    cases.append((mode,['--headless'],['--optimization-check='+mode,'--optimization-report='+str(v/(mode+'.json'))]))
for page in range(2):
    cases.append(('roster'+str(page),[],['--aircraft-test-stage=0','--roster-test-page='+str(page),'--aircraft-test-report='+str(v/('roster'+str(page)+'.json'))]))
for mode in ['title_nocredit','title_freeplay','pause','options','controls','feel','results','gameover','ending','continue','warning','destroyed','weapon0','weapon1','weapon2','weapon3','pickups']:
    switches=['--skin-ui-check='+mode,'--skin-test-report='+str(v/('gui_'+mode+'.json'))]
    if not mode.startswith('title'):
        switches+=['--aircraft-test-stage=0','--aircraft-test-seconds=100']
    cases.append(('gui_'+mode,[],switches))
def run(case):
    name,engine,switches=case
    proc=subprocess.run([str(exe),*engine,'--fixed-fps','60','--log-file',str(v/(name+'.log')),'--','--developer-mode',*switches,'--optimization-save='+str(v/(name+'_save.cfg'))],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW,timeout=40)
    report=json.loads((v/(name+'.json')).read_text(encoding='utf-8'))
    assert proc.returncode==0 and report['success'],(name,proc.returncode,report)
    def locale_check(item):
        if isinstance(item,dict):
            if 'untranslated' in item:assert not item['untranslated'] and not item.get('missing_chinese_glyphs'),(name,item)
            for value in item.values():locale_check(value)
        elif isinstance(item,list):
            for value in item:locale_check(value)
    locale_check(report)
    print(name+' PASS',flush=True)
    return name
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for future in concurrent.futures.as_completed([pool.submit(run,case) for case in cases]):
        future.result()
print('PASS '+str(len(cases))+' checks',flush=True)
