from pathlib import Path
import json, shutil
root=Path(__file__).parent
products=[
('komorebi','Komorebi Engine','typescript','Workflow scheduling','A foundation for typed, event-driven workflows.','Queue jobs, define dependencies, and inspect each run in a single workspace.','layers'),
('bamboo','Bamboo Neural','python','Knowledge discovery','A considered approach to repository intelligence.','Explore a planned retrieval pipeline for documents, embeddings, and cited answers.','brain-circuit'),
('satori','Satori Auth','typescript','Identity infrastructure','Clear boundaries for every application.','A proposed authentication toolkit for session management, permissions, and tenant isolation.','shield-check'),
('origami','Origami Deploy','python','Release automation','Fold complexity into a repeatable release.','A deployment concept centered on validated configuration and reproducible build steps.','git-branch'),
('katana','Katana Actions','typescript','Developer tooling','Keep your delivery pipeline sharp.','A proposed GitHub Actions toolkit for bundle reports and pull-request quality checks.','zap'),
('bonsai','Bonsai Data','python','Data science','Make room for better data.','A data preparation concept for profiling, cleaning, and documenting transformation decisions.','database'),
('shanshui','Shanshui UI','typescript','Interface systems','Interfaces with room to breathe.','An accessible component-library concept with typed APIs and a restrained visual language.','component'),
('sumi','Sumi Pipeline','python','Data orchestration','Bring structure to the stream.','An ingestion framework concept for async processing, observable tasks, and reliable retries.','cpu'),
('kiri','Kiri Network','typescript','Event infrastructure','Connect the parts that matter.','A typed messaging concept for service events, schema validation, and delivery tracking.','network'),
('rinzai','Rinzai Agent','python','AI orchestration','Thoughtful automation, defined limits.','An agent orchestration concept with explicit approvals, sandboxed tasks, and reviewable results.','circle-dot')]
(root/'products.json').write_text(json.dumps([dict(id=p[0],name=p[1],category=p[2],focus=p[3],tagline=p[4],description=p[5],icon=p[6],image=i) for i,p in enumerate(products)],indent=2))
public=root/'dist'
public.mkdir(exist_ok=True)
for name in ['index.html','style.css','animations.css','script.js','config.js','products.json']:
    shutil.copy2(root/name,public/name)
shutil.copytree(root/'assets', public/'assets', dirs_exist_ok=True)
(public/'.nojekyll').touch()
print('Built HealthUp into dist/')
