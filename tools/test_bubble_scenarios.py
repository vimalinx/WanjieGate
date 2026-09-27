import unittest
from backend.bubble_scenarios import questions, resolve
from backend.bubble_catalog import candidates

def decision(scene,interaction='request'):
 return {'answers':{'scene':{'choice':scene,'confidence':.96},'interaction':{'choice':interaction,'confidence':.96},**{str(i):{'noul':.95} for i in range(50)}}}
class Scenarios(unittest.TestCase):
 def test_learning_not_market_or_writing(self):
  text='先别查股价，帮我解释市盈率。'
  r=resolve(text,candidates(text,[]),decision('learning'))
  self.assertTrue(any(x['resource'].get('action')=='explain' for x in r['candidates']))
  self.assertFalse(any('market' in x['resource'] or x['resource'].get('action') in ('write','research') for x in r['candidates']))
 def test_non_requests_have_no_executable_candidates(self):
  for interaction in ('capture','clarify','stop','chat'):
   r=resolve('继续。',candidates('继续。',[]),decision('unknown',interaction))
   self.assertEqual(r['candidates'],[]);self.assertTrue(r['understanding']['message'])
 def test_identity_and_request_bound_to_suggestion(self):
  a=resolve('写甲',candidates('写甲',[]),decision('writing'))['candidates'][0]
  b=resolve('写乙',candidates('写乙',[]),decision('writing'))['candidates'][0]
  self.assertNotEqual(a['id'],b['id']);self.assertEqual(a['request'],'写甲')
 def test_history_not_recommended_by_generic_title(self):
  items=candidates('写股票科普',[{'id':'old','title':'写一篇草稿','kind':'document','version':1,'source':'model','content':{'text':'不相关的读书笔记'}}])
  r=resolve('写股票科普',items,decision('writing'))
  self.assertFalse(any('artifact' in x['resource'] for x in r['candidates']))
 def test_six_scenes_and_examples(self):
  q=questions([])
  self.assertIn('development',q['scene']['criteria']);self.assertIn('停止生成',q['interaction']['instructions'])
 def test_uncertain_requires_clarification(self):
  d=decision('writing');d['answers']['scene']['confidence']=.3
  self.assertEqual(resolve('看看这个',[],d)['understanding']['interaction'],'clarify')
if __name__=='__main__':unittest.main()

class SeedCoverage(unittest.TestCase):
 def test_seed_requests_respect_scene_boundaries(self):
  from backend.bubble_scenarios import SEEDS,ALLOWED
  for sample in SEEDS['examples']:
   scene=sample['expected']['scene']
   if scene not in ALLOWED:continue
   text=sample['utterance'];r=resolve(text,candidates(text,[]),decision(scene))
   for item in r['candidates']:
    action=item['resource'].get('action')
    if action:self.assertIn(action,ALLOWED[scene],sample['id'])

class PresetTests(unittest.TestCase):
 def test_each_scene_has_concrete_presets(self):
  from backend.bubble_presets import PRESETS
  from backend.bubble_scenarios import ALLOWED
  from backend.bubble_catalog import ACTIONS
  for scene in ALLOWED:
   self.assertGreaterEqual(sum(p['scene']==scene for p in PRESETS.values()),4)
  self.assertTrue(set(PRESETS)<=set(ACTIONS))
  self.assertLessEqual(len(candidates('想探索新方向',[])),50)
 def test_no_writing_also_blocks_expansion(self):
  r=resolve('我自己写，不要代写正文',candidates('我自己写，不要代写正文',[]),decision('writing'))
  self.assertFalse(any(x['resource'].get('action') in ('write','expand','polish') for x in r['candidates']))

class WritingConstraints(unittest.TestCase):
 def test_self_written_draft_can_be_polished_when_requested(self):
  text='我自己写了初稿，请帮我润色表达'
  r=resolve(text,candidates(text,[]),decision('writing'))
  self.assertTrue(any(x['resource'].get('action')=='polish' for x in r['candidates']))
  self.assertFalse(any(x['resource'].get('action')=='write' for x in r['candidates']))
