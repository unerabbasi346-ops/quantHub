// Governing specification: Doc 08 — Frontend Architecture (QH-008 v1.0)
//   §Component Standards: reusable design-system component.
// handbook/ui/01_UI_TECHNOLOGY_STANDARD §Component Library: shadcn/ui
//   (Radix primitives) is the FROZEN headless foundation for Dialogs.
// handbook/ui/visual_engineering/05_GLASS_SURFACE_SYSTEM §Modals: "Highest
//   elevation, Stronger blur, Background dimming, Clear visual focus.
//   Opening: Fade + Scale. Closing: Scale + Fade." §Floating Glass Surface:
//   "Must appear visually elevated above every other layer."
// handbook/ui/visual_engineering/09_COMPONENT_BLUEPRINT_LIBRARY §Modal
//   Components: "Glass Surface, Blur Background, Clear Header, Footer
//   Actions ... Never instantly appear."
// Per Doc 00 §14.11
//
// @radix-ui/react-dialog supplies focus trap, ARIA roles (role="dialog",
// aria-modal), Escape-to-close and outside-click — this component only adds
// the QuantHub glass skin and the framer-motion enter/exit. No default
// shadcn/Radix styling ships unstyled (Doc 09 "no component may use generic
// library styling").
'use client'

import { type ReactNode } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import { cn } from '@/lib/utils/cn'
import { CARD_RADIUS } from './Card'

interface ModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: ReactNode
  description?: ReactNode
  children?: ReactNode
  footer?: ReactNode
  /** Doc 09: header height 56-64px scales with content width; widen for data-dense bodies. */
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

const SIZE_CLASSES = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
} as const

export function Modal({ open, onOpenChange, title, description, children, footer, size = 'md', className }: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            {/* Background dimming (Doc 05) — separate layer from the panel's
                own glass, so the panel's blur strength never has to fight an
                override for "stronger blur than a card". */}
            <Dialog.Overlay asChild forceMount>
              <motion.div
                className="fixed inset-0 z-40 bg-bg/70 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15, ease: 'easeOut' }}
              />
            </Dialog.Overlay>
            <div className="fixed inset-0 z-40 flex items-center justify-center p-4">
              <Dialog.Content asChild forceMount>
                <motion.div
                  className={cn(
                    // Floating Glass Surface — strongest blur + elevation in
                    // the system, deliberately beyond Card's `elevated` tier.
                    'relative w-full overflow-hidden border border-border/[0.1] bg-surface-raised/80 shadow-glow backdrop-blur-2xl',
                    CARD_RADIUS,
                    SIZE_CLASSES[size],
                    className,
                  )}
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.97 }}
                  transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
                >
                  <div className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
                    <div>
                      <Dialog.Title className="text-card-title font-medium tracking-tight text-fg">{title}</Dialog.Title>
                      {description && (
                        <Dialog.Description className="mt-1 text-body text-fg-muted">{description}</Dialog.Description>
                      )}
                    </div>
                    <Dialog.Close
                      aria-label="Close"
                      className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-fg-muted transition-colors hover:bg-surface-hover hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
                    >
                      <X size={16} />
                    </Dialog.Close>
                  </div>

                  {children && <div className="px-5 py-4 text-body text-fg">{children}</div>}

                  {footer && (
                    <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-4">{footer}</div>
                  )}
                </motion.div>
              </Dialog.Content>
            </div>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  )
}
