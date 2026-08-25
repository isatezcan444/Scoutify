import React from 'react';
import { Modal, ModalVariant } from './Modal';
import { Button } from './button';
import { Loader2, LucideIcon, Trash2, AlertTriangle } from 'lucide-react';
import { useI18n } from '../../context/I18nContext';

export interface ConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  subtitle?: string;
  message?: React.ReactNode;
  icon?: LucideIcon;
  variant?: ModalVariant;
  confirmText?: string;
  cancelText?: string;
  loading?: boolean;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  subtitle,
  message,
  icon = Trash2,
  variant = 'danger',
  confirmText,
  cancelText,
  loading = false,
}) => {
  const { t } = useI18n();

  // Danger confirms a destructive action; every other tone confirms a neutral one.
  const defaultConfirmLabel =
    variant === 'danger' ? t('common.delete') : t('common.confirm');
  const confirmBtnVariant =
    variant === 'danger' ? 'destructive' : variant === 'warning' ? 'warning' : 'default';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      icon={icon}
      variant={variant}
      maxWidth="md"
      closeOnOutsideClick={!loading}
      footer={
        <>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={loading}
            onClick={onClose}
            className="cursor-pointer"
          >
            {cancelText || t('common.cancel')}
          </Button>
          <Button
            type="button"
            variant={confirmBtnVariant}
            size="sm"
            disabled={loading}
            onClick={onConfirm}
            className="font-bold space-x-1.5 cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>{t('common.loading')}</span>
              </>
            ) : (
              <span>{confirmText || defaultConfirmLabel}</span>
            )}
          </Button>
        </>
      }
    >
      <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-[#25293C] border border-slate-200/60 dark:border-white/[0.05] text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
        {message}
      </div>
    </Modal>
  );
};
