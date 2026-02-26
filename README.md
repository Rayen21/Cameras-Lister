###### 26-02-26更新了blender中3.X——5.X版本中EEVEE渲染器内部ID名称不统一，导致切换渲染器功能失效的问题
#### 由于blender4.2的时候EEVEE渲染器内部名称使用了EEVEE_NEXT这个名称作为和旧版EEVEE时的区别，在5.X时又使用回了EEVEE这个内部ID名称，所以对代码进行了全版本的内部ID适配。

###### 25-12-27更新了blender4.5的一些规范

<img width="626" height="345" alt="image" src="https://github.com/user-attachments/assets/e8f29f60-c450-4c1d-b9b8-8d8300d58ecc" />


#### 感谢这个作者开源的项目 https://github.com/Ryxx/Cameras-Lister

#### 这个作者项目年代有点久远了而且也没有再更新，在他的基础上适配了新版本的blender修改后有了这个插件

## ++++++++++++++++++以下为旧的内容（可以忽略）++++++++++++++++++++

这是一个blener中的相机列表插件（进行了简单的标题汉化，以及修改了对4.2系统中的渲染器切换的代码修改）

基本功能：

1、快捷键alt+c,可以快速显示场景中的相机列表

2、可以快速以当前视图创建相机

3、可以快速设置相机视野和渲染方式

<img width="342" height="249" alt="image" src="https://github.com/user-attachments/assets/c75bc34d-0797-47c8-96c5-d592e8151d23" />

