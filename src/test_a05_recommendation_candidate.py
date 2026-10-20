"""Semantic code fixtures, not manual gold labels or accuracy measurement."""
import unittest
from a05_recommendation_candidate import advise


class RecommendationTests(unittest.TestCase):
    def classify(self,text,word,code,section='',kind='REQUIRED'):
        a=text.index(word)
        e=dict(raw_match_ranges=[[a,a+len(word)]],sentence_text=text,
               normalized_start=a,normalized_end=a+len(word),skill_code=code,
               mention_type=kind,mapping_status='MAPPED_TO_RAW',excerpt=text,
               raw_excerpt_start=0,section=section,rule_id='')
        return advise(e,text)['kind']

    def test_native_not_react(self):
        self.assertEqual(self.classify('Required: React Native experience','React','REACT'),'EXCLUDE')

    def test_packages_not_parent(self):
        for package in ['react-Dom','react-jss']:
            self.assertEqual(self.classify('Required: '+package, 'react','REACT'),'EXCLUDE')

    def test_direct_react_retained(self):
        self.assertEqual(self.classify('Required: React experience','React','REACT'),'REQUIRED')

    def test_azure_products(self):
        self.assertEqual(self.classify('Required: Azure DevOps experience','Azure','AZURE'),'EXCLUDE')
        self.assertEqual(self.classify('Required: Azure cloud experience','Azure','AZURE'),'REQUIRED')

    def test_oracle_product(self):
        self.assertEqual(self.classify('Required: Oracle Cloud experience','Oracle','ORACLE_DB'),'EXCLUDE')
        self.assertIsNone(self.classify('Required: Oracle experience','Oracle','ORACLE_DB'))
        self.assertEqual(self.classify('Required: Oracle Database experience','Oracle Database','ORACLE_DB'),'REQUIRED')

    def test_comparison_not_requirement(self):
        self.assertEqual(self.classify('Knowledge which predates Angular and React','Angular','ANGULAR'),'EXCLUDE')

    def test_optional_heading(self):
        self.assertEqual(self.classify('Additional Nice-to-Haves: SQL knowledge','SQL','SQL'),'PREFERRED')

    def test_local_optional_over_required(self):
        self.assertEqual(self.classify('Required skills: Python experience is a plus','Python','PYTHON'),'PREFERRED')

    def test_title_not_task(self):
        self.assertIsNone(self.classify('AWS Data Engineer','AWS','AWS','ROLE','TASK'))

    def test_intro_not_task(self):
        self.assertIsNone(self.classify('working as a Power BI Semantic Layer Engineer','Power BI','POWER_BI','ROLE','TASK'))
        self.assertIsNone(self.classify('Here is what you will experience working as a Power BI Semantic Layer Engineer','Power BI','POWER_BI'))

    def test_business_requirements_are_task_context(self):
        self.assertEqual(self.classify('Implement business requirements using PHP','PHP','PHP','TASK','TASK'),'TASK')

    def test_expertise_in_task_section_is_requirement(self):
        self.assertEqual(self.classify('Expertise in PHP programming with a focus on Magento development','PHP','PHP','TASK'),'REQUIRED')

    def test_company_and_benefits_stay_excluded(self):
        self.assertEqual(self.classify('Our company develops Python tools','Python','PYTHON',kind='COMPANY_ONLY'),'EXCLUDE')
        self.assertEqual(self.classify('Benefits include Python courses','Python','PYTHON',kind='OUTSIDE_POSITION'),'EXCLUDE')

    def test_real_task(self):
        self.assertEqual(self.classify('You will deploy Docker','Docker','DOCKER','TASK'),'TASK')

    def test_negation_kept(self):
        self.assertEqual(self.classify('No SQL experience required','SQL','SQL',kind='NEGATED'),'EXCLUDE')

    def test_nosql_not_sql(self):
        self.assertEqual(self.classify('Required: no-SQL stores','SQL','SQL'),'EXCLUDE')

    def test_missing_alias_context_not_cured(self):
        self.assertIsNone(self.classify('Required: Go','Go','GO',kind='AMBIGUOUS_ALIAS'))

    def test_heading_after_hit_not_applied(self):
        self.assertEqual(self.classify('Required: Python. Skills Preferred:', 'Python','PYTHON'),'REQUIRED')


if __name__=='__main__':unittest.main()
