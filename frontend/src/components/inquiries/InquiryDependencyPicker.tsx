/**
 * InquiryDependencyPicker - Select blocking inquiries
 *
 * Allows users to mark an inquiry as blocked by other inquiries,
 * creating a dependency chain that affects confidence calculation.
 */

'use client';

import { useState, useMemo } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  CheckIcon,
  XMarkIcon,
  LockClosedIcon,
  LockOpenIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import type { Inquiry } from '@/lib/types/case';

interface InquiryDependencyPickerProps {
  inquiry: Inquiry;
  allInquiries: Inquiry[];
  blockedBy: string[];
  onUpdate: (blockedBy: string[]) => Promise<void>;
  isLoading?: boolean;
}

export function InquiryDependencyPicker({
  inquiry,
  allInquiries,
  blockedBy,
  onUpdate,
  isLoading = false,
}: InquiryDependencyPickerProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>(blockedBy);
  const [search, setSearch] = useState('');
  const [saving, setSaving] = useState(false);

  // Filter out the current inquiry and already resolved ones
  const availableInquiries = useMemo(() => {
    return allInquiries.filter((i) => {
      if (i.id === inquiry.id) return false;
      if (i.status === 'resolved' || i.status === 'archived') return false;
      if (search) {
        return i.title.toLowerCase().includes(search.toLowerCase());
      }
      return true;
    });
  }, [allInquiries, inquiry.id, search]);

  const hasChanges = JSON.stringify(selectedIds.sort()) !== JSON.stringify(blockedBy.sort());

  const handleToggle = (inquiryId: string) => {
    setSelectedIds((prev) =>
      prev.includes(inquiryId)
        ? prev.filter((id) => id !== inquiryId)
        : [...prev, inquiryId]
    );
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await onUpdate(selectedIds);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setSelectedIds(blockedBy);
  };

  // Get inquiry by ID
  const getInquiry = (id: string) => allInquiries.find((i) => i.id === id);

  return (
    <div className="space-y-4">
      {/* Current dependencies display */}
      {blockedBy.length > 0 && (
        <div className="bg-warning-50 border border-warning-200 rounded-lg p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-warning-700 mb-2">
            <LockClosedIcon className="w-4 h-4" />
            Currently blocked by:
          </div>
          <div className="flex flex-wrap gap-2">
            {blockedBy.map((id) => {
              const dep = getInquiry(id);
              return (
                <Badge
                  key={id}
                  variant="warning"
                  className="flex items-center gap-1"
                >
                  {dep?.title || 'Unknown inquiry'}
                </Badge>
              );
            })}
          </div>
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search inquiries..."
          className="w-full pl-9 pr-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-500"
          disabled={isLoading}
        />
      </div>

      {/* Available inquiries */}
      <div className="border rounded-lg divide-y max-h-64 overflow-y-auto">
        {availableInquiries.length === 0 ? (
          <div className="p-4 text-center text-sm text-neutral-500">
            {search
              ? 'No matching inquiries found'
              : 'No available inquiries to add as dependencies'}
          </div>
        ) : (
          availableInquiries.map((inq) => {
            const isSelected = selectedIds.includes(inq.id);
            const statusColor =
              inq.status === 'investigating'
                ? 'text-accent-600 bg-accent-50'
                : 'text-warning-600 bg-warning-50';

            return (
              <button
                key={inq.id}
                onClick={() => handleToggle(inq.id)}
                disabled={isLoading}
                className={`w-full flex items-center gap-3 p-3 text-left transition-colors ${
                  isSelected
                    ? 'bg-accent-50 hover:bg-accent-100'
                    : 'hover:bg-neutral-50'
                }`}
              >
                {/* Checkbox */}
                <div
                  className={`w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 ${
                    isSelected
                      ? 'bg-accent-600 border-accent-600 text-white'
                      : 'border-neutral-300'
                  }`}
                >
                  {isSelected && <CheckIcon className="w-3 h-3" />}
                </div>

                {/* Inquiry details */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-neutral-900 truncate">
                    {inq.title}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={`text-xs px-1.5 py-0.5 rounded ${statusColor}`}>
                      {inq.status}
                    </span>
                    {inq.priority > 0 && (
                      <span className="text-xs text-neutral-500">
                        Priority: {inq.priority}
                      </span>
                    )}
                  </div>
                </div>

                {/* Lock icon for selected */}
                {isSelected && (
                  <LockClosedIcon className="w-4 h-4 text-accent-500 flex-shrink-0" />
                )}
              </button>
            );
          })
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-neutral-500">
          {selectedIds.length} dependenc{selectedIds.length === 1 ? 'y' : 'ies'} selected
        </div>
        <div className="flex gap-2">
          {hasChanges && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleReset}
              disabled={isLoading || saving}
            >
              Reset
            </Button>
          )}
          <Button
            size="sm"
            onClick={handleSave}
            disabled={isLoading || saving || !hasChanges}
          >
            {saving ? 'Saving...' : 'Save Dependencies'}
          </Button>
        </div>
      </div>

      {/* Help text */}
      <p className="text-xs text-neutral-500">
        Marking an inquiry as "blocked by" another indicates that this inquiry
        cannot be fully resolved until the blocking inquiry is resolved first.
        This affects confidence calculations.
      </p>
    </div>
  );
}

/**
 * Compact dependency badge display
 */
export function DependencyBadges({
  blockedBy,
  allInquiries,
  onRemove,
}: {
  blockedBy: string[];
  allInquiries: Inquiry[];
  onRemove?: (id: string) => void;
}) {
  if (blockedBy.length === 0) {
    return null;
  }

  const getInquiry = (id: string) => allInquiries.find((i) => i.id === id);

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-xs text-neutral-500 flex items-center gap-1">
        <LockClosedIcon className="w-3 h-3" />
        Blocked by:
      </span>
      {blockedBy.map((id) => {
        const dep = getInquiry(id);
        return (
          <Badge
            key={id}
            variant="outline"
            className="text-xs flex items-center gap-1 pr-1"
          >
            <span className="truncate max-w-[150px]">
              {dep?.title || 'Unknown'}
            </span>
            {onRemove && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onRemove(id);
                }}
                className="p-0.5 hover:bg-neutral-200 rounded"
              >
                <XMarkIcon className="w-3 h-3" />
              </button>
            )}
          </Badge>
        );
      })}
    </div>
  );
}
