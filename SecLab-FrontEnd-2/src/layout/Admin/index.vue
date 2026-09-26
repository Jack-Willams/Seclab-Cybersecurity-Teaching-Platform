<script setup lang="ts">

import Nav from "./Nav.vue";

</script>

<template>
  <div class="fixed w-full h-full flex bg-base-100">
    <Nav class="w-64 h-full"></Nav>
    <div class="flex-1 flex flex-col">
        <RouterView></RouterView>
    </div>
  </div>
</template>

<style scoped>

</style>
