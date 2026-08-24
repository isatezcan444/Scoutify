import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  Plus, 
  Trash2, 
  Loader2, 
  X, 
  Phone 
} from 'lucide-react';
import { ApiClient } from '../api/client';
import { BlacklistEntry } from '../types';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Card } from '../components/ui/card';

export const BlacklistPage: React.FC = () => {
  const [blacklist, setBlacklist] = useState<BlacklistEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [newPhone, setNewPhone] = useState('');
  const [newReason, setNewReason] = useState('USER_REQUEST');
  const [isAddOpen, setIsAddOpen] = useState(false);

  const fetchBlacklist = async () => {
    setLoading(true);
    try {
      const data = await ApiClient.getBlacklist();
      setBlacklist(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBlacklist();
  }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPhone) return;

    try {
      await ApiClient.addToBlacklist(newPhone, newReason);
      setNewPhone('');
      setIsAddOpen(false);
      fetchBlacklist();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleRemove = async (id: number) => {
    if (!confirm('Bu numarayı kara listeden kaldırmak istediğinize emin misiniz?')) return;
    try {
      await ApiClient.removeFromBlacklist(id);
      fetchBlacklist();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="space-y-6 pb-16 select-none animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-800 dark:text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-[#EA5455]" />
            Kara Liste & Opt-Out Yönetimi ({blacklist.length} Numara)
          </h2>
          <p className="text-xs text-slate-500 dark:text-[#7E7F96] mt-0.5 font-medium">
            İletişim kurulması engellenen veya 'İstemiyorum' yanıtı veren numaralar
          </p>
        </div>

        <Button
          variant="destructive"
          size="sm"
          onClick={() => setIsAddOpen(true)}
          className="space-x-1.5 font-bold"
        >
          <Plus className="w-4 h-4" />
          <span>Kara Listeye Numara Ekle</span>
        </Button>
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 dark:bg-white/[0.02] text-slate-600 dark:text-slate-300 font-bold border-b border-slate-200/80 dark:border-white/[0.08]">
              <tr>
                <th className="py-3.5 px-4">Telefon Numarası</th>
                <th className="py-3.5 px-4">Engelleme Nedeni</th>
                <th className="py-3.5 px-4">Eklenme Tarihi</th>
                <th className="py-3.5 px-4 text-right">İşlemler</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-white/[0.05] text-slate-700 dark:text-slate-300 font-medium">
              {loading ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-400">
                    <Loader2 className="w-5 h-5 animate-spin mx-auto text-[#EA5455]" />
                  </td>
                </tr>
              ) : blacklist.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-10 text-center text-slate-400 font-semibold">
                    Kara listede kayıtlı numara bulunmuyor.
                  </td>
                </tr>
              ) : (
                blacklist.map((entry) => (
                  <tr key={entry.id} className="hover:bg-slate-50/60 dark:hover:bg-white/[0.02]">
                    <td className="py-3.5 px-4 font-mono font-bold text-[#EA5455] flex items-center gap-2">
                      <Phone className="w-3.5 h-3.5" />
                      {entry.phone_e164}
                    </td>
                    <td className="py-3.5 px-4">
                      <Badge variant="danger">
                        {entry.reason}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-slate-500 dark:text-[#7E7F96] font-sans">
                      {new Date(entry.created_at).toLocaleString('tr-TR')}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleRemove(entry.id)}
                        className="text-slate-400 hover:text-[#EA5455] p-1.5 rounded-md hover:bg-[#EA5455]/10 transition-colors"
                        title="Kara Listeden Çıkar"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {isAddOpen && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <form 
            onSubmit={handleAdd} 
            className="vuexy-card max-w-sm w-full p-6 space-y-4 shadow-xl border border-slate-200 dark:border-white/[0.1]"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-800 dark:text-white flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-[#EA5455]" />
                Kara Listeye Ekle
              </h3>
              <button
                type="button"
                onClick={() => setIsAddOpen(false)}
                className="text-slate-400 hover:text-slate-700 dark:hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Telefon Numarası *</label>
                <input
                  type="text"
                  value={newPhone}
                  onChange={(e) => setNewPhone(e.target.value)}
                  placeholder="0532 123 45 67"
                  className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-mono font-bold"
                  required
                />
              </div>

              <div>
                <label className="text-slate-700 dark:text-slate-300 font-bold block mb-1">Engelleme Nedeni</label>
                <select
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg vuexy-input text-xs font-semibold"
                >
                  <option value="USER_REQUEST">Kullanıcı Talebi</option>
                  <option value="OPT_OUT_KEYWORD">Opt-Out Yanıtı (İstemiyorum)</option>
                  <option value="SPAM_REPORT">Spam Şikayeti</option>
                  <option value="INVALID_NUMBER">Geçersiz Numara</option>
                </select>
              </div>
            </div>

            <div className="flex items-center justify-end space-x-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setIsAddOpen(false)}
              >
                İptal
              </Button>
              <Button
                type="submit"
                variant="destructive"
                className="font-bold"
              >
                Kara Listeye Kaydet
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};
