<script setup lang="ts">
withDefaults(defineProps<{ size?: 'sm' | 'md' | 'lg' }>(), { size: 'md' })
</script>

<template>
  <span
    class="tracking-tight"
    :class="{ 'text-lg': size === 'sm', 'text-xl': size === 'md', 'text-2xl': size === 'lg' }"
  ><span class="brand-kit">KIT</span><span class="brand-munic">municator</span></span>
</template>
