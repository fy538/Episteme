/**
 * Popover component built on @floating-ui/react
 */

'use client';

import * as React from 'react';
import {
  useFloating,
  useInteractions,
  useClick,
  useDismiss,
  useRole,
  FloatingPortal,
  FloatingFocusManager,
  offset,
  flip,
  shift,
  autoUpdate,
  Placement,
} from '@floating-ui/react';
import { clsx } from 'clsx';

interface PopoverContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
  refs: ReturnType<typeof useFloating>['refs'];
  floatingStyles: React.CSSProperties;
  context: ReturnType<typeof useFloating>['context'];
  getReferenceProps: ReturnType<typeof useInteractions>['getReferenceProps'];
  getFloatingProps: ReturnType<typeof useInteractions>['getFloatingProps'];
}

const PopoverContext = React.createContext<PopoverContextValue | null>(null);

function usePopoverContext() {
  const context = React.useContext(PopoverContext);
  if (!context) {
    throw new Error('Popover components must be used within a Popover');
  }
  return context;
}

interface PopoverProps {
  children: React.ReactNode;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  placement?: Placement;
}

export function Popover({
  children,
  open: controlledOpen,
  onOpenChange,
  placement = 'bottom-start',
}: PopoverProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(false);

  const open = controlledOpen ?? uncontrolledOpen;
  const setOpen = onOpenChange ?? setUncontrolledOpen;

  const { refs, floatingStyles, context } = useFloating({
    open,
    onOpenChange: setOpen,
    placement,
    middleware: [offset(8), flip(), shift({ padding: 8 })],
    whileElementsMounted: autoUpdate,
  });

  const click = useClick(context);
  const dismiss = useDismiss(context);
  const role = useRole(context);

  const { getReferenceProps, getFloatingProps } = useInteractions([
    click,
    dismiss,
    role,
  ]);

  const value = React.useMemo(
    () => ({
      open,
      setOpen,
      refs,
      floatingStyles,
      context,
      getReferenceProps,
      getFloatingProps,
    }),
    [open, setOpen, refs, floatingStyles, context, getReferenceProps, getFloatingProps]
  );

  return (
    <PopoverContext.Provider value={value}>
      {children}
    </PopoverContext.Provider>
  );
}

interface PopoverTriggerProps {
  children: React.ReactElement;
  asChild?: boolean;
}

export function PopoverTrigger({ children, asChild }: PopoverTriggerProps) {
  const { refs, getReferenceProps } = usePopoverContext();

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, {
      ref: refs.setReference,
      ...getReferenceProps(),
    } as React.HTMLAttributes<Element>);
  }

  return (
    <button ref={refs.setReference} {...getReferenceProps()}>
      {children}
    </button>
  );
}

interface PopoverContentProps {
  children: React.ReactNode;
  className?: string;
  align?: 'start' | 'center' | 'end';
}

export function PopoverContent({
  children,
  className,
}: PopoverContentProps) {
  const { open, refs, floatingStyles, context, getFloatingProps } = usePopoverContext();

  if (!open) return null;

  return (
    <FloatingPortal>
      <FloatingFocusManager context={context} modal={false}>
        <div
          ref={refs.setFloating}
          style={floatingStyles}
          {...getFloatingProps()}
          className={clsx(
            'z-50 bg-white rounded-md shadow-md border border-neutral-200/80 p-4',
            'animate-in fade-in-0 zoom-in-95',
            className
          )}
        >
          {children}
        </div>
      </FloatingFocusManager>
    </FloatingPortal>
  );
}
