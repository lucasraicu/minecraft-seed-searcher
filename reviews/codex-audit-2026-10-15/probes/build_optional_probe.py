from pathlib import Path
p=Path('/tmp/minecraft-audit-20261015');root=Path.cwd()
s=Path(__file__).with_name('build_probe.py').read_text().replace("'audit_batch'","'audit_optional'")
d=(root/'native/blueprint_dynamic.inc').read_text()
old='''    if(w->fixture)return 0;
    int code=nb_capacity(w,bounds);'''
new='''    if(w->fixture) {
        if(slot!=0)return 0;
        int point[2]={56,-800};
        int code=nb_copy(w,&o->raw,point,1);if(code)return code;
        return nb_copy(w,&o->viable,point,1);
    }
    int code=nb_capacity(w,bounds);'''
assert d.count(old)==1
(p/'audit_dynamic.inc').write_text(d.replace(old,new))
(p/'audit_blueprint_batch.inc').write_text((root/'native/blueprint_batch.inc').read_text().replace('"blueprint_dynamic.inc"','"audit_dynamic.inc"'))
s=s.replace('#include "blueprint_batch.inc"','#include "audit_blueprint_batch.inc"').replace("include_dirs=[str(ROOT/'native')","include_dirs=[str(out),str(ROOT/'native')")
exec(compile(s,'build_optional_probe.py','exec'))
