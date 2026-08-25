import React, { useState, useEffect } from 'react';
import { 
  Send, 
  Sparkles, 
  Play, 
  ShieldCheck, 
  Sliders, 
  Clock, 
  Building2, 
  ListPlus,
  Loader2 
} from 'lucide-react';
import { ApiClient } from '../api/client';
import { Campaign } from '../types';
import { 
  Button, 
  Badge, 
  Card, 
  PageHeader, 
  EmptyState 
} from '../components/ui';
import { 
  CampaignCard, 
  SpintaxPreviewCard 
} from '../components/domain';
import { 
  FormField, 
  TextInput, 
  Textarea, 
  Slider, 
  Switch, 
  FormSection 
} from '../components/forms';
import { Stepper } from '../components/navigation';
import { getStoredAntiBanConfig } from '../utils/antiBanSettings';
import { useToast } from '../context/ToastContext';
import { useI18n } from '../context/I18nContext';

interface CampaignsPageProps {
  onRefreshStats: () => void;
}

export const CampaignsPage: React.FC<CampaignsPageProps> = ({ onRefreshStats }) => {
  const toast = useToast();
  const { t } = useI18n();
  const storedConfig = getStoredAntiBanConfig();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'list' | 'builder'>('list');

  // Campaign Builder Form
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [template, setTemplate] = useState(
    "{Hello|Hi|Greetings} {name},\n\nWe noticed your business in {city} {district}. Your {rating} star rating on Google is impressive! 🌟\n\nWe would love to introduce our automated WhatsApp communication platform. Can we share a quick 2-minute overview?\n\n{Best regards|Sincerely}."
  );
  const [minDelay, setMinDelay] = useState(storedConfig.min_delay_seconds);
  const [maxDelay, setMaxDelay] = useState(storedConfig.max_delay_seconds);
  const [typingDelay, setTypingDelay] = useState(storedConfig.typing_delay_seconds);
  const [workingHoursEnabled, setWorkingHoursEnabled] = useState(storedConfig.working_hours_enabled);
  const [workingHoursStart, setWorkingHoursStart] = useState(storedConfig.working_hours_start);
  const [workingHoursEnd, setWorkingHoursEnd] = useState(storedConfig.working_hours_end);
  const [builderStep, setBuilderStep] = useState(0);

  const fetchCampaigns = async () => {
    setLoading(true);
    try {
      const data = await ApiClient.getCampaigns();
      setCampaigns(data);
    } catch (err) {
      console.error('Error fetching campaigns:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const insertTag = (tag: string) => {
    setTemplate((prev) => prev + ` {${tag}}`);
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !template) {
      toast.warning('Please fill in campaign name and message template.', t('common.warning'));
      return;
    }

    try {
      await ApiClient.createCampaign({
        name,
        description,
        message_template: template,
        min_delay_seconds: minDelay,
        max_delay_seconds: maxDelay,
        typing_delay_seconds: typingDelay,
        working_hours_enabled: workingHoursEnabled,
        working_hours_start: workingHoursStart,
        working_hours_end: workingHoursEnd,
      });

      toast.success('Campaign created successfully.', t('common.success'));
      setActiveTab('list');
      setName('');
      setDescription('');
      fetchCampaigns();
      onRefreshStats();
    } catch (err: any) {
      toast.error(err.message || t('common.error'), t('toast.errorTitle'));
    }
  };

  const handleLaunchCampaign = async (campaignId: number) => {
    try {
      await ApiClient.launchCampaign(campaignId, { limit: 50 });
      toast.success('Campaign launched and running safely in the background!', t('common.success'));
      fetchCampaigns();
      onRefreshStats();
    } catch (err: any) {
      toast.error(err.message || t('common.error'), t('toast.errorTitle'));
    }
  };

  const handlePauseCampaign = async (campaignId: number) => {
    try {
      await ApiClient.pauseCampaign(campaignId);
      toast.info(t('campaigns.pauseCampaign'), t('common.info'));
      fetchCampaigns();
      onRefreshStats();
    } catch (err: any) {
      toast.error(err.message || t('common.error'), t('toast.errorTitle'));
    }
  };

  const handleCancelCampaign = async (campaignId: number) => {
    const confirmed = await toast.confirm({
      title: t('campaigns.pauseCampaign') + '?',
      message: 'Are you sure you want to pause this campaign dispatch?',
      confirmText: t('campaigns.pauseCampaign'),
      variant: 'warning',
    });
    if (!confirmed) return;

    try {
      await ApiClient.pauseCampaign(campaignId);
      toast.warning(t('campaigns.pauseCampaign'), t('common.warning'));
      fetchCampaigns();
      onRefreshStats();
    } catch (err: any) {
      toast.error(err.message || t('common.error'), t('toast.errorTitle'));
    }
  };

  return (
    <div className="space-y-6 pb-16 select-none animate-fade-in">
      {/* Top Header & Mode Tabs */}
      <PageHeader
        title={t('campaigns.title')}
        subtitle={t('titles.campaignsSub')}
        icon={Send}
        actions={
          <div className="flex items-center space-x-2">
            <Button
              variant={activeTab === 'list' ? 'outline' : 'ghost'}
              size="sm"
              onClick={() => setActiveTab('list')}
              className={`cursor-pointer ${activeTab === 'list' ? 'border-[#7367F0] text-[#7367F0] font-bold' : ''}`}
            >
              {t('campaigns.title')} ({campaigns.length})
            </Button>
            <Button
              variant={activeTab === 'builder' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setActiveTab('builder')}
              className="space-x-1.5 font-bold shadow-md shadow-[#7367F0]/30 cursor-pointer"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{t('campaigns.createCampaign')}</span>
            </Button>
          </div>
        }
      />

      {activeTab === 'list' ? (
        /* Campaigns List View */
        <div className="space-y-4">
          {campaigns.length === 0 ? (
            <Card className="p-8 text-center">
              <EmptyState
                icon={Send}
                title={t('campaigns.emptyTitle')}
                description={t('campaigns.emptyDescription')}
                action={{
                  label: t('campaigns.createCampaign'),
                  onClick: () => setActiveTab('builder'),
                  icon: Sparkles,
                }}
              />
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {campaigns.map((camp) => (
                <CampaignCard
                  key={camp.id}
                  campaign={camp}
                  onStart={handleLaunchCampaign}
                  onPause={handlePauseCampaign}
                  onCancel={handleCancelCampaign}
                />
              ))}
            </div>
          )}
        </div>
      ) : (
        /* Spintax Studio & Campaign Builder View */
        <form onSubmit={handleCreateCampaign} className="space-y-6">
          <Card className="p-5">
            <Stepper
              currentStep={builderStep}
              onStepClick={(step) => setBuilderStep(step)}
              steps={[
                { id: '1', title: '1. Basic Info', subtitle: 'Name & Targeting' },
                { id: '2', title: '2. Spintax Template', subtitle: 'Dynamic Messages' },
                { id: '3', title: '3. Anti-Ban Jitter', subtitle: 'Timings & Working Hours' },
              ]}
            />
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Form Controls & Template Editor */}
            <div className="lg:col-span-7 space-y-6">
              <Card className="p-6 space-y-5">
                <FormSection
                  title={t('campaigns.templateLabel')}
                  subtitle="Configure dynamic parameters and personalize each outreach dispatch."
                  icon={Sparkles}
                >
                  <FormField label={t('campaigns.campaignName')} required>
                    <TextInput
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. Istanbul Kadıköy Dental Clinics Outreach"
                      required
                    />
                  </FormField>

                  <FormField label="Description">
                    <TextInput
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="e.g. Q3 Outreach with introductory greeting offer"
                    />
                  </FormField>

                  {/* Available Dynamic Field Injection Tags */}
                  <div>
                    <label className="text-xs font-bold text-slate-700 dark:text-slate-200 block mb-1.5">
                      Personalization Variables
                    </label>
                    <div className="flex flex-wrap gap-1.5">
                      {['name', 'city', 'district', 'category', 'rating'].map((tag) => (
                        <button
                          key={tag}
                          type="button"
                          onClick={() => insertTag(tag)}
                          className="text-[11px] font-mono font-bold px-2.5 py-1 rounded-md bg-[#7367F0]/10 text-[#7367F0] hover:bg-[#7367F0]/20 border border-[#7367F0]/20 transition-all cursor-pointer"
                        >
                          +{`{${tag}}`}
                        </button>
                      ))}
                    </div>
                  </div>

                  <FormField label={t('campaigns.templateLabel')} required helperText="Spintax format: {Option A|Option B|Option C}">
                    <Textarea
                      rows={7}
                      value={template}
                      onChange={(e) => setTemplate(e.target.value)}
                      required
                    />
                  </FormField>
                </FormSection>
              </Card>

              {/* Anti-Ban Timings for this Campaign */}
              <Card className="p-6 space-y-5">
                <FormSection
                  title="Anti-Ban Jitter & Delivery Rules"
                  subtitle="Per-campaign cooldown delays to guarantee account safety."
                  icon={ShieldCheck}
                >
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                    <Slider
                      label={t('whatsapp.minDelay')}
                      icon={Clock}
                      value={minDelay}
                      min={15}
                      max={120}
                      step={5}
                      unit="s"
                      onChange={setMinDelay}
                    />

                    <Slider
                      label={t('whatsapp.maxDelay')}
                      icon={Clock}
                      value={maxDelay}
                      min={minDelay + 5}
                      max={240}
                      step={5}
                      unit="s"
                      onChange={setMaxDelay}
                    />
                  </div>

                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Building2 className="w-4 h-4 text-[#7367F0]" />
                        <span className="text-xs font-extrabold text-slate-800 dark:text-white">
                          {t('whatsapp.workingHoursTitle')}
                        </span>
                      </div>
                      <Switch
                        checked={workingHoursEnabled}
                        onChange={setWorkingHoursEnabled}
                      />
                    </div>

                    {workingHoursEnabled && (
                      <div className="grid grid-cols-2 gap-3 pt-2">
                        <FormField label={t('whatsapp.startTime')}>
                          <TextInput
                            type="time"
                            value={workingHoursStart}
                            onChange={(e) => setWorkingHoursStart(e.target.value)}
                          />
                        </FormField>
                        <FormField label={t('whatsapp.endTime')}>
                          <TextInput
                            type="time"
                            value={workingHoursEnd}
                            onChange={(e) => setWorkingHoursEnd(e.target.value)}
                          />
                        </FormField>
                      </div>
                    )}
                  </div>
                </FormSection>
              </Card>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setActiveTab('list')}
                  className="cursor-pointer"
                >
                  {t('common.cancel')}
                </Button>

                <Button
                  type="submit"
                  className="space-x-2 font-bold shadow-md shadow-[#7367F0]/30 cursor-pointer"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>{t('campaigns.startCampaign')}</span>
                </Button>
              </div>
            </div>

            {/* Right Column: Spintax Live Variation Preview Card */}
            <div className="lg:col-span-5 space-y-6">
              <SpintaxPreviewCard template={template} />
            </div>
          </div>
        </form>
      )}
    </div>
  );
};
